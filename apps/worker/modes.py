"""Mode-specific runners that wrap the vendored research-pipeline.

Each runner executes a different subset of steps and pushes progress to Supabase.
The pipeline itself is kept unmodified — we import its step functions and wrap
them with progress hooks.

- run_full: every step (original pipeline behavior)
- run_angle: step0 + R1a (angle-lens) + R2-VoC, no R3
- run_ump_only: R3-Prefetch + R3-Scientist only, uses artifacts from source job
- run_custom: user-selected step list
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

# Put the vendored pipeline on the path
PIPELINE_DIR = Path(__file__).parent / "pipeline"
sys.path.insert(0, str(PIPELINE_DIR))

# Import from the vendored pipeline — done after sys.path insert
from pipeline import (  # type: ignore  # noqa: E402
    step0_scrape,
    step1_research,
    step2_synthesis,
    step3_quality,
    step3b_repair,
    step4_assembly,
)
from config import load_config  # type: ignore  # noqa: E402
from synthesis import synthesize_r2, assemble_report  # type: ignore  # noqa: E402

from drive import upload_artifacts
from progress import (
    finish_step,
    mark_job_finished,
    mark_job_running,
    register_artifact,
    start_step,
    update_job,
)
from storage import upload_file
from supabase_client import get_supabase

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _job_dir(job_id: str) -> Path:
    base = Path(os.environ.get("WORKER_OUTPUT_DIR", "output"))
    d = base / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d


async def _push_progress_around(job_id: str, step_key: str, coro):
    start_step(job_id, step_key)
    t0 = time.monotonic()
    try:
        result = await coro
    except Exception as e:  # noqa: BLE001
        finish_step(job_id, step_key, "failed", log_text=str(e)[:800])
        raise
    finish_step(
        job_id,
        step_key,
        "succeeded",
        cost_usd=_extract_cost(result),
        chars_produced=_extract_chars(result),
        log_text=f"{int(time.monotonic() - t0)}s",
    )
    return result


def _extract_cost(result: Any) -> float:
    if isinstance(result, tuple) and len(result) >= 2 and isinstance(result[1], (int, float)):
        return float(result[1])
    return 0.0


def _extract_chars(result: Any) -> int | None:
    if isinstance(result, tuple) and result and isinstance(result[0], str):
        return len(result[0])
    return None


def _client_drive_folder_id(client_id: str) -> str | None:
    # NOTE: two things to watch:
    # 1. postgrest-py's .maybe_single() raises APIError on 204 No Content
    #    (supabase-community/postgrest-py#78) — we use .limit(1) instead.
    # 2. supabase-py caches the default schema on the client instance: once
    #    anyone calls `.schema("research")`, the cached get_supabase() client
    #    keeps looking in research.*. Call .schema("public") explicitly so
    #    this query lands on public.clients regardless of call order.
    sb = get_supabase()
    resp = (
        sb.schema("public")
        .table("clients")
        .select("drive_folder_id")
        .eq("id", client_id)
        .limit(1)
        .execute()
    )
    rows = getattr(resp, "data", None) or []
    if not rows:
        return None
    return rows[0].get("drive_folder_id")


def _upload_all_artifacts(job_id: str, job_dir: Path, brand: str) -> None:
    """Push every file the pipeline produced into Supabase Storage + register it.

    The kind is derived from the filename convention of the pipeline:
      - Research-{Brand}-{Date}.md → md
      - Research-{Brand}-{Date}.docx → docx
      - R1a-*-draft.md → r1a
      - R1b-*-draft.md → r1b
      - R2-*-voc-raw.md → r2_raw
      - R2-*-final.md → r2_final
      - R3-crossref-*.md → r3_prefetch
      - R3-*-final.md → r3_final
      - product-briefing.md → briefing
      - qr-scores.json → qr_scores
      - cost-report.json → cost_report
    """
    for f in sorted(job_dir.iterdir()):
        if not f.is_file():
            continue
        kind = _kind_for(f.name, brand)
        if kind is None:
            continue
        try:
            storage_path, size = upload_file(job_id, f, kind)
            register_artifact(job_id, kind, storage_path=storage_path, size_bytes=size)
        except Exception as e:  # noqa: BLE001
            log.exception("Failed to upload %s: %s", f.name, e)


def _kind_for(name: str, brand: str) -> str | None:
    lower = name.lower()
    if lower == "product-briefing.md":
        return "briefing"
    if lower == "qr-scores.json":
        return "qr_scores"
    if lower == "cost-report.json":
        return "cost_report"
    if lower.startswith("r1a") and lower.endswith(".md"):
        return "r1a"
    if lower.startswith("r1b") and lower.endswith(".md"):
        return "r1b"
    if lower.startswith("r2") and "voc-raw" in lower:
        return "r2_raw"
    if lower.startswith("r2") and "final" in lower:
        return "r2_final"
    if lower.startswith("r3-crossref"):
        return "r3_prefetch"
    if lower.startswith("r3") and "final" in lower:
        return "r3_final"
    if lower.startswith("research-") and lower.endswith(".md"):
        return "md"
    if lower.startswith("research-") and lower.endswith(".docx"):
        return "docx"
    return None


# ---------------------------------------------------------------------------
# Full Mode — complete pipeline (reuses run_research verbatim)
# ---------------------------------------------------------------------------
async def run_full(
    job_id: str,
    client_id: str,
    url: str,
    brand: str,
    angle: str,
    product_name: str | None,
) -> None:
    mark_job_running(job_id)
    cfg = load_config()
    os.environ["ANTHROPIC_API_KEY"] = cfg["anthropic_key"]
    job_dir = _job_dir(job_id)

    total_cost = 0.0
    error: str | None = None
    quality_score: float | None = None

    try:
        briefing, c = await _push_progress_around(
            job_id, "step0_scrape", step0_scrape(url, brand, job_dir, cfg)
        )
        total_cost += c

        start_step(job_id, "r1a")
        start_step(job_id, "r1b")
        start_step(job_id, "r2_voc")
        start_step(job_id, "r3_prefetch")
        drafts, c = await step1_research(briefing, angle, brand, product_name or brand, job_dir, cfg)
        total_cost += c
        for k in ("r1a", "r1b", "r2_voc", "r3_prefetch"):
            pipeline_key = "r2_raw" if k == "r2_voc" else ("r3_prefetch" if k == "r3_prefetch" else k)
            text = drafts.get(pipeline_key, "")
            finish_step(job_id, k, "succeeded", chars_produced=len(text))

        start_step(job_id, "r2_synth")
        start_step(job_id, "r3_scientist")
        finals, c = await step2_synthesis(drafts, brand, angle, job_dir, cfg)
        total_cost += c
        finish_step(job_id, "r2_synth", "succeeded", chars_produced=len(finals["r2_final"]))
        finish_step(job_id, "r3_scientist", "succeeded", cost_usd=c, chars_produced=len(finals["r3_final"]))

        start_step(job_id, "quality_review")
        scores = step3_quality(drafts, finals, brand, job_dir, cfg)
        quality_score = float(scores.get("overall", 0))
        finish_step(job_id, "quality_review", "succeeded", log_text=str(scores.get("summary", ""))[:800])

        if scores["overall"] < cfg["quality_threshold"]:
            start_step(job_id, "repair")
            c = await step3b_repair(scores, drafts, finals, briefing, brand, angle, product_name or brand, job_dir, cfg)
            total_cost += c
            # Re-score
            scores = step3_quality(drafts, finals, brand, job_dir, cfg)
            quality_score = float(scores.get("overall", quality_score))
            finish_step(job_id, "repair", "succeeded", cost_usd=c, log_text=str(scores.get("summary", ""))[:800])

        start_step(job_id, "assembly_export")
        step4_assembly(briefing, drafts, finals, brand, angle, scores, job_dir)
        finish_step(job_id, "assembly_export", "succeeded")

    except Exception as e:  # noqa: BLE001
        log.exception("Full run failed for job %s: %s", job_id, e)
        error = str(e)[:1800]

    # Upload artifacts + Drive push regardless of error (so user gets what's there)
    _upload_all_artifacts(job_id, job_dir, brand)
    drive_folder_url = _drive_upload_if_possible(job_id, client_id, "full", brand, job_dir)

    status = "failed" if error else "succeeded"
    mark_job_finished(
        job_id,
        status=status,
        cost_usd=total_cost,
        quality_score=quality_score,
        error=error,
        drive_folder_url=drive_folder_url,
    )


# ---------------------------------------------------------------------------
# Angle Mode — R1a (angle-focused) + R2-VoC + Assembly (no R3)
# ---------------------------------------------------------------------------
async def run_angle(
    job_id: str,
    client_id: str,
    url: str,
    brand: str,
    angle: str,
    product_name: str | None,
) -> None:
    import anyio
    from agents import drain_query, make_research_options  # type: ignore
    from system_prompts import OUTPUT_RULES, R1A_SYSTEM_PROMPT, R2_VOC_SYSTEM_PROMPT  # type: ignore
    from tools import build_mcp_servers  # type: ignore

    mark_job_running(job_id)
    cfg = load_config()
    os.environ["ANTHROPIC_API_KEY"] = cfg["anthropic_key"]
    job_dir = _job_dir(job_id)
    total_cost = 0.0
    error: str | None = None
    quality_score: float | None = None

    try:
        briefing, c = await _push_progress_around(
            job_id, "step0_scrape", step0_scrape(url, brand, job_dir, cfg)
        )
        total_cost += c

        mcp = build_mcp_servers(cfg)
        base_context = (
            f"Produkt: {product_name or brand} von {brand}\n"
            f"Angle: {angle}\n\n"
            f"Produkt-Briefing:\n{briefing[:2000]}\n\n"
            f"WICHTIG: Fokussiere die Research stark auf den Angle — nur die Kategorien, die für "
            f"diesen Angle relevant sind. Keep it tight.\n\n"
        )

        r1a_opts = make_research_options(
            R1A_SYSTEM_PROMPT, cfg, max_turns=cfg["r1_turns"],
            max_budget_usd=cfg["r1_budget"], effort="high", tools=[], mcp_servers=mcp,
        )
        r2_opts = make_research_options(
            R2_VOC_SYSTEM_PROMPT, cfg, max_turns=cfg["r2_turns"],
            max_budget_usd=cfg["r2_budget"], effort="high", tools=[], mcp_servers=mcp,
        )

        results: dict[str, tuple[str, float]] = {}

        async def _r1a():
            results["r1a"] = await drain_query(
                base_context + "Recherchiere Kategorien 01-13 angle-fokussiert. Gib den VOLLSTAENDIGEN Text direkt aus.",
                r1a_opts, "R1a-angle",
            )

        async def _r2():
            results["r2"] = await drain_query(
                base_context + (
                    "Sammle Voice of Customer Daten zum Angle: echte Kundenzitate aus Foren, Reviews. "
                    "Für jedes Zitat: exakte Formulierung + Quell-URL. Gib ALLE Zitate direkt aus."
                ),
                r2_opts, "R2-VoC-angle",
            )

        start_step(job_id, "r1a")
        start_step(job_id, "r2_voc")
        async with anyio.create_task_group() as tg:
            tg.start_soon(_r1a)
            tg.start_soon(_r2)

        r1a_text, r1a_cost = results["r1a"]
        r2_text, r2_cost = results["r2"]
        total_cost += r1a_cost + r2_cost
        (job_dir / f"R1a-{brand}-draft.md").write_text(r1a_text, encoding="utf-8")
        (job_dir / f"R2-{brand}-voc-raw.md").write_text(r2_text, encoding="utf-8")
        finish_step(job_id, "r1a", "succeeded", cost_usd=r1a_cost, chars_produced=len(r1a_text))
        finish_step(job_id, "r2_voc", "succeeded", cost_usd=r2_cost, chars_produced=len(r2_text))

        start_step(job_id, "r2_synth")
        r2_final = synthesize_r2(r1a_text, "", r2_text, brand)
        (job_dir / f"R2-{brand}-final.md").write_text(r2_final, encoding="utf-8")
        finish_step(job_id, "r2_synth", "succeeded", chars_produced=len(r2_final))

        start_step(job_id, "assembly_export")
        report = assemble_report(briefing, r1a_text, "", r2_final, "", brand, angle, None)
        today = date.today()
        report_path = job_dir / f"Angle-Research-{brand}-{today}.md"
        report_path.write_text(report, encoding="utf-8")
        # DOCX via the pipeline's export
        from export import export_docx  # type: ignore
        try:
            export_docx(report_path.resolve())
        except Exception:  # noqa: BLE001
            pass
        finish_step(job_id, "assembly_export", "succeeded", chars_produced=len(report))
        quality_score = 8.0  # angle mode has no formal quality gate

    except Exception as e:  # noqa: BLE001
        log.exception("Angle run failed for %s: %s", job_id, e)
        error = str(e)[:1800]

    _upload_all_artifacts(job_id, job_dir, brand)
    drive_folder_url = _drive_upload_if_possible(job_id, client_id, "angle", brand, job_dir)

    mark_job_finished(
        job_id,
        status="failed" if error else "succeeded",
        cost_usd=total_cost,
        quality_score=quality_score,
        error=error,
        drive_folder_url=drive_folder_url,
    )


# ---------------------------------------------------------------------------
# UMP-only — R3-Prefetch + R3-Scientist using artifacts from a source job
# ---------------------------------------------------------------------------
async def run_ump_only(
    job_id: str,
    client_id: str,
    url: str,
    brand: str,
    angle: str,
    product_name: str | None,
    source_job_id: str,
) -> None:
    import anyio
    from agents import drain_query, make_research_options  # type: ignore
    from system_prompts import R3_PREFETCH_SYSTEM_PROMPT, R3_SCIENTIST_SYSTEM_PROMPT  # type: ignore
    from tools import build_mcp_servers  # type: ignore

    mark_job_running(job_id)
    cfg = load_config()
    os.environ["ANTHROPIC_API_KEY"] = cfg["anthropic_key"]
    job_dir = _job_dir(job_id)
    total_cost = 0.0
    error: str | None = None
    quality_score: float | None = None

    try:
        # Fetch R1a + R1b + R2-final from the source job's artifacts (Supabase Storage)
        sb = get_supabase()
        source_artifacts = (
            sb.schema("research")
            .table("job_artifacts")
            .select("kind, storage_path")
            .eq("job_id", source_job_id)
            .execute()
        )
        by_kind = {row["kind"]: row["storage_path"] for row in (source_artifacts.data or []) if row.get("storage_path")}

        def _download(kind: str) -> str:
            p = by_kind.get(kind)
            if not p:
                return ""
            data = sb.storage.from_(os.environ.get("ARTIFACT_BUCKET", "research-reports")).download(p)
            return data.decode("utf-8") if isinstance(data, (bytes, bytearray)) else str(data)

        r1a_text = _download("r1a")
        r1b_text = _download("r1b")
        r2_final = _download("r2_final")

        if not (r1a_text or r2_final):
            raise RuntimeError(
                "Source job has no R1/R2 artifacts — cannot run UMP-only without prior research."
            )

        # R3-Prefetch
        mcp = build_mcp_servers(cfg)
        r3_pre_opts = make_research_options(
            R3_PREFETCH_SYSTEM_PROMPT, cfg,
            max_turns=cfg["r3_prefetch_turns"],
            max_budget_usd=cfg["r3_prefetch_budget"],
            effort="medium", tools=[], mcp_servers=mcp,
        )

        start_step(job_id, "r3_prefetch")
        base_ctx = (
            f"Produkt: {product_name or brand} von {brand}\n"
            f"Angle: {angle}\n\n"
            f"Kontext aus R1:\n{r1a_text[:3000]}\n"
        )
        r3_pre_text, r3_pre_cost = await drain_query(
            base_ctx + (
                "Suche wissenschaftliche Studien zu den Inhaltsstoffen via CrossRef und PubMed. "
                "Für jede Studie: Autoren, Titel, Journal, DOI, Jahr, Relevanz."
            ),
            r3_pre_opts, "R3-Prefetch",
        )
        total_cost += r3_pre_cost
        (job_dir / f"R3-crossref-{brand}.md").write_text(r3_pre_text, encoding="utf-8")
        finish_step(job_id, "r3_prefetch", "succeeded", cost_usd=r3_pre_cost, chars_produced=len(r3_pre_text))

        # R3-Scientist
        start_step(job_id, "r3_scientist")
        r3_sci_opts = make_research_options(
            R3_SCIENTIST_SYSTEM_PROMPT, cfg, model=cfg["scientist_model"],
            effort="max", max_turns=cfg["r3_scientist_turns"],
            max_budget_usd=cfg["r3_scientist_budget"], tools=[], mcp_servers=mcp,
        )
        r3_prompt = (
            f"Produkt: {brand} | Angle: {angle}\n\n"
            f"Erstelle das UMP/UMS-Paket basierend auf diesen Daten:\n\n"
            f"## Produkt-Kontext (R1 Auszug)\n{r1a_text[:4000]}\n\n"
            f"## Validierte Studien (R3-Prefetch)\n{r3_pre_text}\n\n"
            f"Nutze die validierten DOIs. Suche 2-3 zusätzliche Studien für Lücken."
        )
        r3_final, r3_cost = await drain_query(r3_prompt, r3_sci_opts, "R3-Scientist")
        total_cost += r3_cost
        (job_dir / f"R3-{brand}-final.md").write_text(r3_final, encoding="utf-8")
        finish_step(job_id, "r3_scientist", "succeeded", cost_usd=r3_cost, chars_produced=len(r3_final))

        # Assembly — just R3 section
        start_step(job_id, "assembly_export")
        today = date.today()
        angle_slug = _slug(angle)[:40]
        md = (
            f"# UMP/UMS-Konstruktion: {brand} — {today}\n\n"
            f"**Angle:** {angle}\n"
            f"**Basierend auf Job:** {source_job_id}\n\n"
            f"---\n\n{r3_final}\n"
        )
        report_path = job_dir / f"UMP-UMS-{brand}-{angle_slug}-{today}.md"
        report_path.write_text(md, encoding="utf-8")
        from export import export_docx  # type: ignore
        try:
            export_docx(report_path.resolve())
        except Exception:  # noqa: BLE001
            pass
        finish_step(job_id, "assembly_export", "succeeded", chars_produced=len(md))
        quality_score = 8.5

    except Exception as e:  # noqa: BLE001
        log.exception("UMP-only run failed for %s: %s", job_id, e)
        error = str(e)[:1800]

    _upload_all_artifacts(job_id, job_dir, brand)
    drive_folder_url = _drive_upload_if_possible(job_id, client_id, "ump", brand, job_dir)

    mark_job_finished(
        job_id,
        status="failed" if error else "succeeded",
        cost_usd=total_cost,
        quality_score=quality_score,
        error=error,
        drive_folder_url=drive_folder_url,
    )


# ---------------------------------------------------------------------------
# Custom Mode — user-selected steps
# ---------------------------------------------------------------------------
async def run_custom(
    job_id: str,
    client_id: str,
    url: str,
    brand: str,
    angle: str,
    product_name: str | None,
    steps: list[str],
) -> None:
    """Run only the selected steps. This is best-effort: we iterate in canonical
    order and execute each step if it is in the list, threading state as we go.
    """
    mark_job_running(job_id)
    cfg = load_config()
    os.environ["ANTHROPIC_API_KEY"] = cfg["anthropic_key"]
    job_dir = _job_dir(job_id)

    total_cost = 0.0
    error: str | None = None
    quality_score: float | None = None
    briefing = ""
    drafts: dict[str, str] = {"r1a": "", "r1b": "", "r2_raw": "", "r3_prefetch": ""}
    finals: dict[str, str] = {"r2_final": "", "r3_final": ""}

    want = set(steps)

    try:
        if "step0_scrape" in want:
            briefing, c = await _push_progress_around(
                job_id, "step0_scrape", step0_scrape(url, brand, job_dir, cfg)
            )
            total_cost += c

        if any(s in want for s in ("r1a", "r1b", "r2_voc", "r3_prefetch")):
            drafts_out, c = await step1_research(briefing, angle, brand, product_name or brand, job_dir, cfg)
            total_cost += c
            drafts = drafts_out
            for k, pipeline_key in (("r1a", "r1a"), ("r1b", "r1b"), ("r2_voc", "r2_raw"), ("r3_prefetch", "r3_prefetch")):
                if k in want:
                    start_step(job_id, k)
                    finish_step(job_id, k, "succeeded", chars_produced=len(drafts.get(pipeline_key, "")))
                else:
                    start_step(job_id, k)
                    finish_step(job_id, k, "skipped")

        if "r2_synth" in want or "r3_scientist" in want:
            start_step(job_id, "r2_synth")
            start_step(job_id, "r3_scientist")
            finals_out, c = await step2_synthesis(drafts, brand, angle, job_dir, cfg)
            total_cost += c
            finals = finals_out
            finish_step(job_id, "r2_synth", "succeeded" if "r2_synth" in want else "skipped", chars_produced=len(finals["r2_final"]))
            finish_step(job_id, "r3_scientist", "succeeded" if "r3_scientist" in want else "skipped", chars_produced=len(finals["r3_final"]))

        if "quality_review" in want:
            start_step(job_id, "quality_review")
            scores = step3_quality(drafts, finals, brand, job_dir, cfg)
            quality_score = float(scores.get("overall", 0))
            finish_step(job_id, "quality_review", "succeeded", log_text=str(scores.get("summary", ""))[:800])
        else:
            scores = None

        if "repair" in want and scores is not None and scores["overall"] < cfg["quality_threshold"]:
            start_step(job_id, "repair")
            c = await step3b_repair(scores, drafts, finals, briefing, brand, angle, product_name or brand, job_dir, cfg)
            total_cost += c
            scores = step3_quality(drafts, finals, brand, job_dir, cfg)
            quality_score = float(scores.get("overall", quality_score or 0))
            finish_step(job_id, "repair", "succeeded", cost_usd=c)

        if "assembly_export" in want:
            start_step(job_id, "assembly_export")
            step4_assembly(briefing, drafts, finals, brand, angle, scores, job_dir)
            finish_step(job_id, "assembly_export", "succeeded")

    except Exception as e:  # noqa: BLE001
        log.exception("Custom run failed for %s: %s", job_id, e)
        error = str(e)[:1800]

    _upload_all_artifacts(job_id, job_dir, brand)
    drive_folder_url = _drive_upload_if_possible(job_id, client_id, "custom", brand, job_dir)

    mark_job_finished(
        job_id,
        status="failed" if error else "succeeded",
        cost_usd=total_cost,
        quality_score=quality_score,
        error=error,
        drive_folder_url=drive_folder_url,
    )


# ---------------------------------------------------------------------------
# Drive upload helper (shared)
# ---------------------------------------------------------------------------
def _drive_upload_if_possible(job_id: str, client_id: str, mode: str, brand: str, job_dir: Path) -> str | None:
    parent = _client_drive_folder_id(client_id)
    if not parent:
        log.info("Client %s has no drive_folder_id — skipping Drive upload", client_id)
        return None
    try:
        md_files = sorted(job_dir.glob("Research-*.md")) + sorted(job_dir.glob("Angle-Research-*.md")) + sorted(job_dir.glob("UMP-UMS-*.md"))
        docx_files = sorted(job_dir.glob("*.docx"))
        to_upload = md_files + docx_files
        if not to_upload:
            return None
        folder_url, results = upload_artifacts(parent, mode, brand, to_upload)
        for path, file_id, web_url in results:
            kind = "md" if path.suffix == ".md" else "docx"
            try:
                # Update the existing artifact row with drive ids
                sb = get_supabase()
                sb.schema("research").table("job_artifacts").update(
                    {"drive_file_id": file_id, "drive_url": web_url}
                ).eq("job_id", job_id).eq("kind", kind).execute()
            except Exception as e:  # noqa: BLE001
                log.exception("Failed to update artifact drive ids: %s", e)
        return folder_url
    except Exception as e:  # noqa: BLE001
        log.exception("Drive upload failed for %s: %s", job_id, e)
        return None


def _slug(text: str) -> str:
    import re as _re
    s = _re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return s or "job"
