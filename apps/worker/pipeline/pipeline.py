#!/usr/bin/env python3
"""Ecomtorials Research Pipeline — SDK Agent Team Orchestrator.

Standalone CLI tool that produces a complete Marketing Research Report
(25 categories + VoC + UMP/UMS + sources) as MD/DOCX/PDF.

Usage:
    python pipeline.py --url "https://..." --brand "VedaNaturals" --angle "..."

Pattern: drain_query() + anyio.create_task_group() — validated from content agent pipeline.
"""

import argparse
import json
import os
import sys
import time
from datetime import date
from pathlib import Path

import re

import anyio
import httpx

# Ensure our package is importable
sys.path.insert(0, str(Path(__file__).parent))

from agents import drain_query, make_research_options  # noqa: E402
from config import load_config, QUALITY_THRESHOLD  # noqa: E402
from export import export_docx, export_pdf  # noqa: E402
from synthesis import synthesize_r2, assemble_report  # noqa: E402
from system_prompts import (  # noqa: E402
    OUTPUT_RULES,
    R1A_SYSTEM_PROMPT,
    R1B_SYSTEM_PROMPT,
    R2_VOC_SYSTEM_PROMPT,
    R3_PREFETCH_SYSTEM_PROMPT,
    R3_SCIENTIST_SYSTEM_PROMPT,
)
from tools import build_mcp_servers  # noqa: E402


# Module-level constants
_CAT_PATTERNS = [r"Kat\.?\s*{n:02d}", r"### {n:02d}", r"Kategorie {n:02d}"]

_EMPTY_PAGE_INDICATORS = [
    "nicht verfügbar", "nicht verfuegbar", "nicht möglich", "nicht moeglich",
    "keine produktdaten", "seite gelöscht", "seite geloescht",
    "seite gibt es nicht mehr", "nicht analysierbar", "404",
    "keine inhaltsstoffe", "keine claims",
]


def _find_missing_categories(text: str) -> list[int]:
    """Return list of category numbers (01-25) NOT found in text."""
    missing = []
    for cat_num in range(1, 26):
        if not any(re.search(p.format(n=cat_num), text, re.IGNORECASE) for p in _CAT_PATTERNS):
            missing.append(cat_num)
    return missing


def _read_fallback(job_dir: Path, pattern: str) -> str:
    """If drain_query returned empty, check if agent wrote a file anyway."""
    for f in sorted(job_dir.glob(pattern)):
        content = f.read_text(encoding="utf-8").strip()
        if content and len(content) > 50:
            print(f"[FALLBACK] Reading agent file: {f.name} ({len(content)}c)", file=sys.stderr)
            return content
    return ""


# ---------------------------------------------------------------------------
# Step 0: Product Scrape + Briefing (httpx + toolless Agent)
# ---------------------------------------------------------------------------
async def step0_scrape(
    url: str, brand: str, job_dir: Path, cfg: dict
) -> tuple[str, float]:
    """Scrape product URL with httpx, then analyze with a toolless agent."""
    print("\n[STEP 0] Product Scrape + Briefing...", file=sys.stderr)

    # 1. Scrape: Jina Reader primary, httpx fallback
    from jina_reader import jina_read
    content, jina_ok = await jina_read(url)
    if jina_ok:
        html = content
        print(f"[STEP 0] Jina scraped {len(html)}c from {url}", file=sys.stderr)
    else:
        print(f"[STEP 0] Jina failed, trying httpx fallback...", file=sys.stderr)
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
                resp = await client.get(url)
                html = resp.text[:20000]
            print(f"[STEP 0] httpx fallback: {len(html)}c from {url}", file=sys.stderr)
        except Exception as e:
            print(f"[STEP 0] Both scrapers failed: {e}", file=sys.stderr)
            html = f"(Scrape fehlgeschlagen: {e})"

    # 2. Analyze with toolless agent
    system_prompt = (
        "Du bist ein Produkt-Analyst. Analysiere den HTML-Inhalt und extrahiere:\n"
        "1. Produktname, Marke, Preis\n"
        "2. Alle Inhaltsstoffe (INCI-Namen wenn vorhanden)\n"
        "3. Claims und Versprechen des Herstellers\n"
        "4. Zielgruppe (aus Tonalitaet und Messaging)\n"
        "5. Branche/Nische\n\n"
        "Formatiere als Markdown. Sprache: Deutsch."
        + OUTPUT_RULES
    )

    opts = make_research_options(
        system_prompt=system_prompt,
        cfg=cfg,
        model=cfg["research_model"],
        effort="medium",
        max_turns=cfg["step0_turns"],
        max_budget_usd=cfg["step0_budget"],
        tools=[],  # No tools — HTML already scraped
    )

    prompt = f"Analysiere den folgenden Inhalt von {url} (Marke: {brand}):\n\n{html}"
    result, cost = await drain_query(prompt, opts, "Step0-Analyse")

    if not result:
        result = f"# Produkt-Briefing: {brand}\nURL: {url}\n(Analyse fehlgeschlagen)"

    briefing_path = job_dir / "product-briefing.md"
    briefing_path.write_text(result, encoding="utf-8")
    print(f"[STEP 0] Done: {len(result)}c, ${cost:.4f}", file=sys.stderr)

    # Validation gate: check if we got actual product data
    lower_result = result.lower()
    hit_count = sum(1 for ind in _EMPTY_PAGE_INDICATORS if ind in lower_result)
    if hit_count >= 3:
        print(
            f"\n[STEP 0] ABORT: Product page appears empty/deleted "
            f"({hit_count} empty-indicators found).\n"
            f"[STEP 0] The pipeline would produce generic market research, not product-specific.\n"
            f"[STEP 0] Please provide a valid, accessible product URL.\n"
            f"[STEP 0] Briefing saved to: {briefing_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    return result, cost


# ---------------------------------------------------------------------------
# Step 1: Research — R1a + R1b + R2-VoC + R3-Prefetch fully parallel
# ---------------------------------------------------------------------------
async def step1_research(
    briefing: str,
    angle: str,
    brand: str,
    product_name: str,
    job_dir: Path,
    cfg: dict,
) -> tuple[dict[str, str], float]:
    """All 4 research agents run in parallel. Rate limits are handled at the
    Perplexity tool layer via retry+exponential backoff (see mcp-server/tools/perplexity.py).
    """
    print("\n[STEP 1] 4-way parallel: R1a + R1b + R2-VoC + R3-Prefetch...", file=sys.stderr)

    mcp = build_mcp_servers(cfg)

    base_context = (
        f"Produkt: {product_name} von {brand}\n"
        f"Angle: {angle}\n\n"
        f"Produkt-Briefing:\n{briefing[:2000]}\n\n"
    )

    r1a_opts = make_research_options(R1A_SYSTEM_PROMPT, cfg, max_turns=cfg["r1_turns"],
                                     max_budget_usd=cfg["r1_budget"],
                                     effort="high",
                                     tools=[], mcp_servers=mcp)
    r1b_opts = make_research_options(R1B_SYSTEM_PROMPT, cfg, max_turns=cfg["r1_turns"],
                                     max_budget_usd=cfg["r1_budget"],
                                     effort="high",
                                     tools=[], mcp_servers=mcp)
    r2_opts = make_research_options(R2_VOC_SYSTEM_PROMPT, cfg, max_turns=cfg["r2_turns"],
                                    max_budget_usd=cfg["r2_budget"],
                                    effort="high",
                                    tools=[], mcp_servers=mcp)
    r3_opts = make_research_options(R3_PREFETCH_SYSTEM_PROMPT, cfg,
                                    max_turns=cfg["r3_prefetch_turns"],
                                    max_budget_usd=cfg["r3_prefetch_budget"],
                                    effort="medium",
                                    tools=[], mcp_servers=mcp)

    results: dict[str, tuple[str, float]] = {}

    async def _r1a():
        results["r1a"] = await drain_query(
            base_context + "Recherchiere Kategorien 01-13. Gib den VOLLSTAENDIGEN Research-Text direkt aus.",
            r1a_opts, "R1a"
        )

    async def _r1b():
        results["r1b"] = await drain_query(
            base_context + "Recherchiere Kategorien 14-25. Gib den VOLLSTAENDIGEN Research-Text direkt aus.",
            r1b_opts, "R1b"
        )

    async def _r2():
        results["r2"] = await drain_query(
            base_context + (
                "Sammle Voice of Customer Daten: echte Kundenzitate aus Foren, Reviews, Reddit, Trustpilot. "
                "Fuer jedes Zitat: exakte Formulierung + Quell-URL. "
                "Kategorien: Physical Problem, Emotional Problem, Failed Solutions, Belief Breaks, "
                "Physical Benefit, Emotional Benefit, Aha-Moment, Wunschzustand. "
                "Gib ALLE Zitate direkt als Text aus."
            ),
            r2_opts, "R2-VoC"
        )

    async def _r3():
        results["r3"] = await drain_query(
            base_context + (
                "Suche wissenschaftliche Studien zu den Inhaltsstoffen via CrossRef und PubMed. "
                "Fuer jede Studie: Autoren, Titel, Journal, DOI, Jahr, Relevanz. "
                "Gib alle gefundenen Studien direkt als Text aus."
            ),
            r3_opts, "R3-Prefetch"
        )

    t0 = time.monotonic()
    async with anyio.create_task_group() as tg:
        tg.start_soon(_r1a)
        tg.start_soon(_r1b)
        tg.start_soon(_r2)
        tg.start_soon(_r3)
    total_elapsed = time.monotonic() - t0

    r1a_text, r1a_cost = results["r1a"]
    r1b_text, r1b_cost = results["r1b"]
    r2_text, r2_cost = results["r2"]
    r3_text, r3_cost = results["r3"]

    # --- Write files ---
    total_cost = r1a_cost + r1b_cost + r2_cost + r3_cost

    drafts = {"r1a": r1a_text, "r1b": r1b_text, "r2_raw": r2_text, "r3_prefetch": r3_text}
    files = {
        "r1a": f"R1a-{brand}-draft.md", "r1b": f"R1b-{brand}-draft.md",
        "r2_raw": f"R2-{brand}-voc-raw.md", "r3_prefetch": f"R3-crossref-{brand}.md",
    }
    for key, fname in files.items():
        (job_dir / fname).write_text(drafts[key], encoding="utf-8")

    print(
        f"[STEP 1] Done: {total_elapsed:.0f}s, "
        f"R1a={len(r1a_text)}c, R1b={len(r1b_text)}c, "
        f"R2={len(r2_text)}c, R3pre={len(r3_text)}c, "
        f"${total_cost:.4f}",
        file=sys.stderr,
    )
    return drafts, total_cost


# ---------------------------------------------------------------------------
# Step 2: Synthesis — R2 programmatic, R3-Scientist agent with MCP
# ---------------------------------------------------------------------------
async def step2_synthesis(
    drafts: dict[str, str],
    brand: str,
    angle: str,
    job_dir: Path,
    cfg: dict,
) -> tuple[dict[str, str], float]:
    """R2: programmatic Python merge. R3-Scientist: Opus agent with MCP tools."""
    print("\n[STEP 2] Synthesis...", file=sys.stderr)

    # R2: Programmatic synthesis (no agent, no cost, instant)
    print("[STEP 2] R2-Synth: programmatic merge...", file=sys.stderr)
    r2_final = synthesize_r2(drafts["r1a"], drafts["r1b"], drafts["r2_raw"], brand)
    (job_dir / f"R2-{brand}-final.md").write_text(r2_final, encoding="utf-8")
    print(f"[STEP 2] R2-Synth: {len(r2_final)}c (programmatic, $0)", file=sys.stderr)

    # R3-Scientist: Opus agent with MCP tools (needs to search + validate DOIs)
    print("[STEP 2] R3-Scientist: Opus agent with MCP...", file=sys.stderr)
    mcp = build_mcp_servers(cfg)

    r3_sci_opts = make_research_options(
        R3_SCIENTIST_SYSTEM_PROMPT, cfg, model=cfg["scientist_model"],
        effort="max",
        max_turns=cfg["r3_scientist_turns"], max_budget_usd=cfg["r3_scientist_budget"],
        tools=[], mcp_servers=mcp,
    )

    r3_sci_prompt = (
        f"Produkt: {brand} | Angle: {angle}\n\n"
        f"Erstelle das UMP/UMS-Paket basierend auf diesen Daten:\n\n"
        f"## Produkt-Kontext (R1 Auszug)\n{drafts['r1a'][:4000]}\n\n"
        f"## Bereits validierte Studien (R3-Prefetch)\n{drafts['r3_prefetch']}\n\n"
        f"Nutze die bereits validierten DOIs aus dem Prefetch. "
        f"Suche 2-3 zusaetzliche Studien fuer Luecken im Mechanismus."
    )

    t0 = time.monotonic()
    r3_final, r3_cost = await drain_query(r3_sci_prompt, r3_sci_opts, "R3-Scientist")
    elapsed = time.monotonic() - t0

    if not r3_final:
        r3_final = _read_fallback(job_dir, "R3-*final*")
    if not r3_final:
        # Use prefetch as fallback
        r3_final = f"## R3 — Studien (Prefetch)\n\n{drafts['r3_prefetch']}"

    (job_dir / f"R3-{brand}-final.md").write_text(r3_final, encoding="utf-8")

    finals = {"r2_final": r2_final, "r3_final": r3_final}
    print(
        f"[STEP 2] Done: {elapsed:.0f}s, "
        f"R2={len(r2_final)}c (programmatic), R3={len(r3_final)}c, ${r3_cost:.4f}",
        file=sys.stderr,
    )
    return finals, r3_cost


# ---------------------------------------------------------------------------
# Step 3: Quality Review (programmatic — no agent)
# ---------------------------------------------------------------------------
def step3_quality(
    drafts: dict[str, str],
    finals: dict[str, str],
    brand: str,
    job_dir: Path,
    cfg: dict,
) -> dict:
    """Programmatic quality review — count categories, sources, DOIs.

    Previous agent-based QR failed consistently: the QR agent tried to verify
    URLs with WebFetch (no tools available) and returned empty results in v4-v6.
    Programmatic scoring is deterministic, instant, and free.
    """
    print("\n[STEP 3] Quality Review (programmatic)...", file=sys.stderr)

    r1_text = drafts["r1a"] + "\n" + drafts["r1b"]
    r2_text = finals["r2_final"]
    r3_text = finals["r3_final"]
    all_text = r1_text + "\n" + r2_text + "\n" + r3_text

    issues_r1r2: list[str] = []
    issues_r3: list[str] = []

    # Q1: Source coverage — count URLs
    url_count = len(re.findall(r'https?://[^\s\)\]]+', all_text))
    if url_count < 15:
        issues_r1r2.append(f"Nur {url_count} URLs gefunden (min 15 empfohlen)")

    # Q2: Category completeness — check R1 categories
    missing_cats = _find_missing_categories(r1_text)
    r1_cats_found = 25 - len(missing_cats)
    if r1_cats_found < 20:
        issues_r1r2.append(f"Nur {r1_cats_found}/25 R1-Kategorien gefunden (min 20)")

    # Q3: R2 VoC — check categories present
    r2_cats = len(re.findall(r'Kat\.\s*\d|Physical Problem|Emotional Problem|Failed Solution|Belief Break|Physical Benefit|Emotional Benefit|Aha-Moment|Wunschzustand', r2_text, re.IGNORECASE))
    if r2_cats < 4:
        issues_r1r2.append(f"R2 VoC: nur {r2_cats} Kategorien erkannt (min 6)")

    # Q4: R2 quote count
    quote_count = len(re.findall(r'"[^"]{20,}"', r2_text))
    if quote_count < 10:
        issues_r1r2.append(f"R2: nur {quote_count} Kundenzitate (min 15 empfohlen)")

    # Q5: R3 DOI count
    doi_count = len(re.findall(r'10\.\d{4,}/[^\s\)]+', r3_text))
    if doi_count < 3:
        issues_r3.append(f"R3: nur {doi_count} DOIs (min 5 empfohlen)")

    # Q6: R3 UMP/UMS presence
    has_ump = bool(re.search(r'UMP|Unique Mechanism of Problem', r3_text, re.IGNORECASE))
    has_ums = bool(re.search(r'UMS|Unique Mechanism of Solution', r3_text, re.IGNORECASE))
    if not has_ump:
        issues_r3.append("UMP (Unique Mechanism of Problem) fehlt")
    if not has_ums:
        issues_r3.append("UMS (Unique Mechanism of Solution) fehlt")

    # Q7: Killer-Hooks
    has_hooks = bool(re.search(r'Hook|PARADOX|TABUBRUCH|INDUSTRIE', r3_text, re.IGNORECASE))
    if not has_hooks:
        issues_r3.append("Killer-Hooks fehlen")

    # Q8: Product specificity — brand name should appear frequently
    brand_lower = brand.lower()
    brand_mentions = all_text.lower().count(brand_lower)
    is_product_specific = brand_mentions >= 10
    if not is_product_specific:
        issues_r1r2.append(
            f"Geringe Produktspezifitaet: '{brand}' nur {brand_mentions}x erwaehnt (min 10)"
        )

    # Score calculation
    r1r2_score = 10.0
    if r1_cats_found < 25:
        r1r2_score -= (25 - r1_cats_found) * 0.3
    if r2_cats < 8:
        r1r2_score -= (8 - r2_cats) * 0.3
    if quote_count < 15:
        r1r2_score -= max(0, (15 - quote_count) * 0.1)
    if url_count < 30:
        r1r2_score -= max(0, (30 - url_count) * 0.05)
    if not is_product_specific:
        r1r2_score -= 2.0  # Heavy penalty for generic content
    r1r2_score = max(1.0, min(10.0, round(r1r2_score, 1)))

    r3_score = 10.0
    if doi_count < 5:
        r3_score -= (5 - doi_count) * 0.8
    if not has_ump:
        r3_score -= 2.0
    if not has_ums:
        r3_score -= 2.0
    if not has_hooks:
        r3_score -= 1.0
    r3_score = max(1.0, min(10.0, round(r3_score, 1)))

    overall = round((r1r2_score + r3_score) / 2, 1)

    scores = {
        "qr_r1r2": {"score": r1r2_score, "issues": issues_r1r2},
        "qr_r3": {"score": r3_score, "issues": issues_r3},
        "overall": overall,
        "summary": (
            f"R1: {r1_cats_found}/25 Kategorien, {url_count} URLs. "
            f"R2: {r2_cats} VoC-Kategorien, {quote_count} Zitate. "
            f"R3: {doi_count} DOIs, UMP={'ja' if has_ump else 'nein'}, "
            f"UMS={'ja' if has_ums else 'nein'}, Hooks={'ja' if has_hooks else 'nein'}. "
            f"Produktspezifisch={'ja' if is_product_specific else 'nein'} ({brand_mentions}x '{brand}')."
        ),
        "metrics": {
            "r1_categories": r1_cats_found,
            "url_count": url_count,
            "r2_voc_categories": r2_cats,
            "quote_count": quote_count,
            "doi_count": doi_count,
            "has_ump": has_ump,
            "has_ums": has_ums,
            "has_hooks": has_hooks,
            "brand_mentions": brand_mentions,
            "is_product_specific": is_product_specific,
        },
    }

    (job_dir / "qr-scores.json").write_text(
        json.dumps(scores, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(
        f"[STEP 3] Done: Overall={overall}/10, "
        f"R1R2={r1r2_score}, R3={r3_score} (programmatic, $0)",
        file=sys.stderr,
    )
    print(f"[STEP 3] {scores['summary']}", file=sys.stderr)

    if overall < cfg["quality_threshold"]:
        print(
            f"[STEP 3] WARNING: Score {overall} < threshold {cfg['quality_threshold']}!",
            file=sys.stderr,
        )

    return scores


# ---------------------------------------------------------------------------
# Step 3b: Targeted Repair — re-run only the weakest step
# ---------------------------------------------------------------------------
async def step3b_repair(
    scores: dict,
    drafts: dict[str, str],
    finals: dict[str, str],
    briefing: str,
    brand: str,
    angle: str,
    product_name: str,
    job_dir: Path,
    cfg: dict,
) -> float:
    """Identify the weakest area from QR issues and re-run only that agent.

    Mutates drafts/finals in-place. Returns repair cost.
    """
    r1r2_issues = scores.get("qr_r1r2", {}).get("issues", [])
    r3_issues = scores.get("qr_r3", {}).get("issues", [])
    r1r2_score = scores.get("qr_r1r2", {}).get("score", 10)
    r3_score = scores.get("qr_r3", {}).get("score", 10)
    metrics = scores.get("metrics", {})

    if r3_score <= r1r2_score and r3_issues:
        return await _repair_r3(
            metrics, drafts, finals, brand, angle, job_dir, cfg
        )
    elif r1r2_issues:
        return await _repair_r1r2(
            metrics, drafts, finals, briefing,
            brand, angle, product_name, job_dir, cfg
        )
    return 0.0


async def _repair_r3(
    metrics: dict, drafts: dict, finals: dict,
    brand: str, angle: str, job_dir: Path, cfg: dict,
) -> float:
    """Repair R3: missing DOIs, UMP/UMS, or hooks."""
    missing = []
    if metrics.get("doi_count", 0) < 5:
        missing.append(f"nur {metrics['doi_count']} DOIs — finde mindestens {5 - metrics['doi_count']} weitere validierte Studien")
    if not metrics.get("has_ump"):
        missing.append("UMP (Unique Mechanism of Problem) fehlt komplett")
    if not metrics.get("has_ums"):
        missing.append("UMS (Unique Mechanism of Solution) fehlt komplett")
    if not metrics.get("has_hooks"):
        missing.append("Killer-Hooks (PARADOX/TABUBRUCH/INDUSTRIE) fehlen")

    if not missing:
        return 0.0

    gap_list = "\n".join(f"- {m}" for m in missing)
    print(f"\n[REPAIR] R3 gaps: {', '.join(missing)}", file=sys.stderr)

    mcp = build_mcp_servers(cfg)
    repair_prompt = (
        f"Produkt: {brand} | Angle: {angle}\n\n"
        f"## Bisheriger R3-Output (unvollstaendig)\n{finals['r3_final'][:3000]}\n\n"
        f"## Luecken die du schliessen musst\n{gap_list}\n\n"
        f"Ergaenze NUR die fehlenden Teile. Nutze CrossRef/PubMed fuer neue DOIs. "
        f"Gib den ERGAENZTEN Text direkt aus — kein Wiederholen des bestehenden Teils."
    )

    opts = make_research_options(
        R3_SCIENTIST_SYSTEM_PROMPT, cfg, model=cfg["scientist_model"],
        effort="high",
        max_turns=cfg["repair_turns"], max_budget_usd=cfg["repair_r3_budget"],
        tools=[], mcp_servers=mcp,
    )

    patch, cost = await drain_query(repair_prompt, opts, "R3-Repair")
    if patch and len(patch) > 100:
        finals["r3_final"] = finals["r3_final"] + "\n\n---\n\n## Ergaenzung (Repair)\n\n" + patch
        (job_dir / f"R3-{brand}-final.md").write_text(finals["r3_final"], encoding="utf-8")
        print(f"[REPAIR] R3 patched: +{len(patch)}c, ${cost:.4f}", file=sys.stderr)
    else:
        print(f"[REPAIR] R3 repair returned insufficient data, skipping", file=sys.stderr)

    return cost


async def _repair_r1r2(
    metrics: dict, drafts: dict, finals: dict,
    briefing: str, brand: str, angle: str, product_name: str,
    job_dir: Path, cfg: dict,
) -> float:
    """Repair R1/R2: missing categories or insufficient VoC quotes."""
    quote_count = metrics.get("quote_count", 99)
    missing_cats = _find_missing_categories(drafts["r1a"] + "\n" + drafts["r1b"])

    if missing_cats:
        # Repair missing R1 categories
        in_r1a = [c for c in missing_cats if c <= 13]
        in_r1b = [c for c in missing_cats if c > 13]
        target = "R1a" if len(in_r1a) >= len(in_r1b) else "R1b"
        target_cats = in_r1a if target == "R1a" else in_r1b
        target_prompt_cls = R1A_SYSTEM_PROMPT if target == "R1a" else R1B_SYSTEM_PROMPT

        cat_str = ", ".join(f"{c:02d}" for c in target_cats)
        print(f"\n[REPAIR] {target}: missing categories {cat_str}", file=sys.stderr)

        mcp = build_mcp_servers(cfg)
        repair_prompt = (
            f"Produkt: {product_name} von {brand}\nAngle: {angle}\n"
            f"Produkt-Briefing:\n{briefing[:1500]}\n\n"
            f"Du musst NUR die folgenden fehlenden Kategorien recherchieren: {cat_str}\n"
            f"Gib den Text fuer diese Kategorien direkt aus."
        )
        opts = make_research_options(
            target_prompt_cls, cfg, max_turns=cfg["repair_turns"],
            max_budget_usd=cfg["repair_r1_budget"], effort="high",
            tools=[], mcp_servers=mcp,
        )
        patch, cost = await drain_query(repair_prompt, opts, f"{target}-Repair")
        if patch and len(patch) > 100:
            key = "r1a" if target == "R1a" else "r1b"
            drafts[key] = drafts[key] + "\n\n---\n\n## Ergaenzung (Repair)\n\n" + patch
            (job_dir / f"{target}-{brand}-draft.md").write_text(drafts[key], encoding="utf-8")
            # Re-synthesize R2 with updated R1
            finals["r2_final"] = synthesize_r2(drafts["r1a"], drafts["r1b"], drafts["r2_raw"], brand)
            (job_dir / f"R2-{brand}-final.md").write_text(finals["r2_final"], encoding="utf-8")
            print(f"[REPAIR] {target} patched: +{len(patch)}c, R2 re-synthesized, ${cost:.4f}", file=sys.stderr)
        return cost

    elif quote_count < 10:
        # Repair R2 VoC — too few quotes
        print(f"\n[REPAIR] R2-VoC: only {quote_count} quotes, need more", file=sys.stderr)
        mcp = build_mcp_servers(cfg)
        repair_prompt = (
            f"Produkt: {product_name} von {brand}\nAngle: {angle}\n\n"
            f"Bisherige Zitate: {quote_count}. Du brauchst mindestens 10 weitere ECHTE Kundenzitate "
            f"aus Foren, Reddit, Trustpilot, Amazon Reviews. "
            f"Fuer jedes Zitat: exakte Formulierung + Quell-URL. Gib NUR die neuen Zitate aus."
        )
        opts = make_research_options(
            R2_VOC_SYSTEM_PROMPT, cfg, max_turns=cfg["repair_turns"],
            max_budget_usd=cfg["repair_r2_budget"], effort="high",
            tools=[], mcp_servers=mcp,
        )
        patch, cost = await drain_query(repair_prompt, opts, "R2-VoC-Repair")
        if patch and len(patch) > 100:
            drafts["r2_raw"] = drafts["r2_raw"] + "\n\n---\n\n## Ergaenzung (Repair)\n\n" + patch
            (job_dir / f"R2-{brand}-voc-raw.md").write_text(drafts["r2_raw"], encoding="utf-8")
            finals["r2_final"] = synthesize_r2(drafts["r1a"], drafts["r1b"], drafts["r2_raw"], brand)
            (job_dir / f"R2-{brand}-final.md").write_text(finals["r2_final"], encoding="utf-8")
            print(f"[REPAIR] R2-VoC patched: +{len(patch)}c, R2 re-synthesized, ${cost:.4f}", file=sys.stderr)
        return cost

    return 0.0


# ---------------------------------------------------------------------------
# Step 4: Assembly + Export (programmatic �� no agent)
# ---------------------------------------------------------------------------
def step4_assembly(
    briefing: str,
    drafts: dict[str, str],
    finals: dict[str, str],
    brand: str,
    angle: str,
    scores: dict | None,
    job_dir: Path,
) -> Path:
    """Programmatic assembly — merge all sections + export. No agent, no cost."""
    print("\n[STEP 4] Assembly + Export (programmatic)...", file=sys.stderr)

    result = assemble_report(
        briefing=briefing,
        r1a=drafts["r1a"],
        r1b=drafts["r1b"],
        r2_synthesized=finals["r2_final"],
        r3_final=finals["r3_final"],
        brand=brand,
        angle=angle,
        scores=scores,
    )

    report_name = f"Research-{brand}-{date.today()}"
    report_path = job_dir / f"{report_name}.md"
    report_path.write_text(result, encoding="utf-8")

    docx_path = export_docx(report_path.resolve())
    pdf_path = export_pdf(report_path.resolve())

    print(
        f"[STEP 4] Done: {report_path} ({len(result)}c, programmatic, $0)"
        + (f", {docx_path}" if docx_path else "")
        + (f", {pdf_path}" if pdf_path else ""),
        file=sys.stderr,
    )

    return report_path


# ---------------------------------------------------------------------------
# Main Orchestrator
# ---------------------------------------------------------------------------
async def run_research(
    url: str,
    angle: str,
    brand: str,
    product_name: str = "",
    output_dir: str | None = None,
) -> dict:
    """Run the complete research pipeline."""
    cfg = load_config()

    os.environ["ANTHROPIC_API_KEY"] = cfg["anthropic_key"]

    today = date.today()
    job_dir = Path(output_dir) if output_dir else Path(f"output/{brand}-{today}")
    job_dir.mkdir(parents=True, exist_ok=True)

    product_name = product_name or brand
    costs: dict[str, float] = {}
    pipeline_start = time.monotonic()

    print(f"\n{'='*60}", file=sys.stderr)
    print(f"  Ecomtorials Research Pipeline", file=sys.stderr)
    print(f"  Brand: {brand} | Angle: {angle}", file=sys.stderr)
    print(f"  URL: {url}", file=sys.stderr)
    print(f"  Output: {job_dir}", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)

    # Step 0: Scrape
    briefing, costs["step0"] = await step0_scrape(url, brand, job_dir, cfg)

    # Step 1: Research (R1 parallel, R2+R3 sequential)
    drafts, costs["step1"] = await step1_research(
        briefing, angle, brand, product_name, job_dir, cfg
    )

    # Step 2: Synthesis (R2 programmatic, R3 Opus agent)
    finals, costs["step2"] = await step2_synthesis(drafts, brand, angle, job_dir, cfg)

    # Step 3: Quality Review (programmatic — no agent, no cost)
    scores = step3_quality(drafts, finals, brand, job_dir, cfg)
    costs["step3"] = 0.0

    # Step 3b: Repair loop — if score below threshold, re-run weakest agent
    costs["repair"] = 0.0
    if scores["overall"] < cfg["quality_threshold"]:
        for i in range(cfg["max_repair_iterations"]):
            print(
                f"\n[REPAIR] Iteration {i+1}/{cfg['max_repair_iterations']} "
                f"(score {scores['overall']} < {cfg['quality_threshold']})",
                file=sys.stderr,
            )
            costs["repair"] += await step3b_repair(
                scores, drafts, finals, briefing,
                brand, angle, product_name, job_dir, cfg,
            )

            # Re-score after repair
            scores = step3_quality(drafts, finals, brand, job_dir, cfg)
            if scores["overall"] >= cfg["quality_threshold"]:
                print(f"[REPAIR] Score now {scores['overall']} — threshold met", file=sys.stderr)
                break
        else:
            print(
                f"[REPAIR] Max iterations reached, score {scores['overall']}",
                file=sys.stderr,
            )

    # Step 4: Assembly + Export (programmatic — no agent, no cost)
    report_path = step4_assembly(briefing, drafts, finals, brand, angle, scores, job_dir)
    costs["step4"] = 0.0

    # Final summary
    total_cost = sum(costs.values())
    elapsed = time.monotonic() - pipeline_start
    elapsed_min = int(elapsed // 60)
    elapsed_sec = int(elapsed % 60)

    overall_score = scores.get("overall", 0)

    cost_report = {
        "brand": brand,
        "date": str(today),
        "steps": costs,
        "total_usd": round(total_cost, 4),
        "runtime_seconds": round(elapsed, 1),
        "quality_score": overall_score,
    }
    (job_dir / "cost-report.json").write_text(
        json.dumps(cost_report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"\n{'='*60}", file=sys.stderr)
    print(f"  Research Pipeline Complete", file=sys.stderr)
    print(f"  Report: {report_path}", file=sys.stderr)
    print(f"  Score:  {overall_score}/10", file=sys.stderr)
    print(f"  Cost:   ${total_cost:.4f}", file=sys.stderr)
    for step, c in costs.items():
        print(f"          {step}: ${c:.4f}", file=sys.stderr)
    print(f"  Time:   {elapsed_min}m {elapsed_sec}s", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)

    return {
        "report": str(report_path),
        "job_dir": str(job_dir),
        "scores": scores,
        "cost": cost_report,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Ecomtorials Research Pipeline — Marketing Research Report Generator"
    )
    parser.add_argument("--url", required=True, help="Product URL to research")
    parser.add_argument("--brand", required=True, help="Brand name")
    parser.add_argument("--angle", default="", help="Research angle/theme")
    parser.add_argument("--product-name", default="", help="Product name (defaults to brand)")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    args = parser.parse_args()

    result = anyio.run(
        run_research,
        args.url,
        args.angle or f"Marketing-Research fuer {args.brand}",
        args.brand,
        args.product_name,
        args.output_dir,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
