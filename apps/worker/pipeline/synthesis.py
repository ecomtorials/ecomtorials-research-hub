"""Programmatic synthesis — merges R1/R2/R3 drafts into final report WITHOUT agents.

Step 2 (R2-Synthesizer) and Step 4 (Assembly) replaced by deterministic Python logic.
No LLM calls, no token cost, instant execution.
"""

import re
from datetime import date


def synthesize_r2(r1a: str, r1b: str, r2_raw: str, brand: str) -> str:
    """Merge R1 + R2 VoC into Belief Architecture section.

    Extracts belief breaks, skeptic arguments, and emotional drivers
    from the raw VoC data and structures them.
    """
    sections = []
    sections.append(f"## Sektion 2: Voice of Customer + Belief Architecture — {brand}\n")

    # Pass through R2 VoC data as-is (already structured by agent)
    if r2_raw.strip():
        sections.append("### 2.1 Authentische Kundenzitate\n")
        sections.append(_clean_agent_output(r2_raw))
    else:
        sections.append("> ⚠️ R2 VoC-Daten nicht verfuegbar.\n")

    # Extract belief breaks from R1 (Kat. 09) if present
    belief_section = _extract_kat_section(r1a + "\n" + r1b, "09")
    if belief_section:
        sections.append("\n### 2.2 Belief Breaks (aus R1 Kat. 09)\n")
        sections.append(belief_section)

    # Extract skeptic arguments from R1 (Kat. 20-22)
    skeptic_section = ""
    for kat in ("20", "21", "22"):
        s = _extract_kat_section(r1b, kat)
        if s:
            skeptic_section += s + "\n\n"
    if skeptic_section.strip():
        sections.append("\n### 2.3 Skeptiker-Argumente + Barrieren (aus R1 Kat. 20-22)\n")
        sections.append(skeptic_section.strip())

    # Extract trigger events from R1 (Kat. 10)
    trigger_section = _extract_kat_section(r1a, "10")
    if trigger_section:
        sections.append("\n### 2.4 Trigger-Events (aus R1 Kat. 10)\n")
        sections.append(trigger_section)

    return "\n\n".join(sections)


def assemble_report(
    briefing: str,
    r1a: str,
    r1b: str,
    r2_synthesized: str,
    r3_final: str,
    brand: str,
    angle: str,
    scores: dict | None = None,
    mode: str = "full",
) -> str:
    """Assemble final Research Report from all components.

    mode controls which sections are rendered:
      - "full": all sections (R1a + R1b + R2 + R3 + Quality scores)
      - "angle": R1a + R2 only (no R1b, no R3, no quality gate)
      - "ump_only": R3 section + references to source Full-Research
    """
    today = date.today()

    # QR scores: prefer explicit scores dict, fall back to mode defaults
    def _fmt_score(v):
        if v is None:
            return "—"
        if isinstance(v, (int, float)):
            return f"{float(v):.1f}"
        return str(v)

    score_r1r2 = scores.get("qr_r1r2", {}).get("score") if scores else None
    score_r3 = scores.get("qr_r3", {}).get("score") if scores else None
    overall = scores.get("overall") if scores else None

    # Count sources
    url_count = len(re.findall(r"https?://[^\s\)]+", r1a + r1b + r2_synthesized + r3_final))
    doi_count = len(re.findall(r"10\.\d{4,}/", r3_final))

    parts = []

    # Mode label for header
    mode_label = {
        "full": "Full Research",
        "angle": "Angle-based Research",
        "ump_only": "Unique Mechanism Development",
        "custom": "Custom Research",
    }.get(mode, "Research")

    # Header
    parts.append(f"# Research Report: {brand} — {today}\n")
    parts.append(f"**Produkt:** {brand}")
    parts.append(f"**Angle:** {angle}")
    parts.append(f"**Modus:** {mode_label}")
    parts.append(f"**Markt:** DACH (primaer Deutschland)")
    parts.append(f"**Erstellt:** {today}")

    # Only show QR scores when we actually have them (Full mode with quality gate).
    # Angle mode skips the quality gate by design — showing "?/10" reads as failure.
    if mode == "full" and any(v is not None for v in (score_r1r2, score_r3, overall)):
        parts.append(
            f"**QR-Scores:** R1/R2: {_fmt_score(score_r1r2)}/10 | "
            f"R3: {_fmt_score(score_r3)}/10 | Gesamt: {_fmt_score(overall)}/10"
        )
    parts.append(f"**Quellen gesamt:** ~{url_count} URLs, {doi_count} DOIs\n")
    parts.append("---\n")

    # Section 1: Zielgruppenanalyse (R1a + R1b)
    has_r1 = bool(r1a.strip() or r1b.strip())
    if has_r1:
        parts.append("## Sektion 1: Zielgruppenanalyse\n")
        if r1a.strip():
            parts.append("### Kategorien 01-13\n")
            parts.append(_clean_agent_output(r1a))
        if r1b.strip():
            parts.append("\n### Kategorien 14-25\n")
            parts.append(_clean_agent_output(r1b))
        parts.append("\n---\n")

    # Section 2: VoC + Belief Architecture (synthesized) — skip if empty
    if r2_synthesized and r2_synthesized.strip():
        parts.append(r2_synthesized)
        parts.append("\n---\n")

    # Section 3: Wissenschaftliche Evidenz (R3) — only when R3 actually ran
    if r3_final and r3_final.strip():
        parts.append(f"## Sektion 3: Wissenschaftliche Evidenz + UMP/UMS — {brand}\n")
        parts.append(_clean_agent_output(r3_final))
        parts.append("\n---\n")
    elif mode == "full":
        # Full mode expected R3 but it produced nothing — that IS a warning
        parts.append(f"## Sektion 3: Wissenschaftliche Evidenz + UMP/UMS — {brand}\n")
        parts.append("> ⚠️ R3 Wissenschaftliche Evidenz nicht verfuegbar.\n")
        parts.append("\n---\n")
    # For angle / ump_only modes: no R3 by design → silently omit the section

    parts.append(f"\n---\n*Research Report erstellt: {today}*\n")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Section extraction
# ---------------------------------------------------------------------------
#
# Match markdown headers like "### Kat. 10: Trigger-Events" or "## Kat 9".
# Permissive on the separator (., :, —) and whitespace; strict on the
# requirement that the line starts with a markdown header marker — otherwise
# a bullet line mentioning the word "Trigger" inside Kat. 05 would false-match.
_KAT_HEADER_RE = re.compile(
    r"^(#+\s*)Kat(?:egorie)?\.?\s*0?(\d{1,2})\b", re.IGNORECASE
)


def _extract_kat_section(text: str, kat_num: str) -> str:
    """Extract one `### Kat. NN …` block from markdown text.

    Matches only on real markdown headers (line starts with `#`), so a
    passing mention of "Trigger" or "Kat. 10" in a bullet of another
    category doesn't bleed into the result.
    """
    if not text:
        return ""
    target = int(kat_num)
    lines = text.split("\n")
    collecting = False
    collected: list[str] = []
    for line in lines:
        m = _KAT_HEADER_RE.match(line)
        if m:
            num = int(m.group(2))
            if num == target:
                collecting = True
                collected.append(line)
                continue
            if collecting:
                # Next Kat header — stop.
                break
        elif collecting:
            # Also stop at unrelated major headers (## Section, # Title).
            if re.match(r"^#{1,2}\s+(?!Kat)", line):
                break
            collected.append(line)
    # Trim trailing blank lines
    while collected and not collected[-1].strip():
        collected.pop()
    return "\n".join(collected).strip()


# ---------------------------------------------------------------------------
# Agent output cleanup
# ---------------------------------------------------------------------------
#
# Agents sometimes prefix their structured output with planning chatter like
# "Alle Daten gesammelt. Jetzt kompiliere ich..." These strings are internal
# to the agent's reasoning and should never appear in the final report. We
# strip them anywhere they occur on their own paragraph, not just at the start
# of the draft.
_CHATTER_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"^(Alle|Ich habe( jetzt)?( alle)?)\s+[Dd]aten\s+gesammelt.*$",
        r"^Genug\s+Material\s+gesammelt.*$",
        r"^Jetzt\s+(kompiliere|erstelle|beginne|starte|gebe|schreibe)\b.*$",
        r"^Nun\s+(kompiliere|erstelle|beginne|folgen)\b.*$",
        r"^Hier\s+(ist|sind|kommt|folgt)\s+(das|der|die|nun)\b.*$",
        r"^Lass\s+mich\b.*$",
        r"^Ich\s+(werde|beginne|starte|kompiliere|erstelle|gebe)\b.*$",
        r"^Basierend\s+auf\s+den?\s+[Dd]aten\b.*$",
        r"^Ok(ay)?,?\s+(ich|hier|jetzt|lass|los)\b.*$",
        r"^Gut,?\s+(ich|hier|jetzt|dann|los)\b.*$",
        # Agent meta-comments about output format
        r"^.{0,80}(kompiliere|formatiere|strukturiere)\s+.*(jetzt|nun)\s+(das|den|die).*",
    ]
]

_FILE_PATH_RE = re.compile(r"^.*R1[ab]?-Draft\s+erstellt:.*$", re.IGNORECASE)
_HOME_PATH_RE = re.compile(r"^.*`/home/.*\.md`.*$")


def _is_chatter(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    return any(p.match(stripped) for p in _CHATTER_PATTERNS)


def _clean_agent_output(text: str) -> str:
    """Remove agent artifacts: preamble, interleaved chatter, file paths, repair tables."""
    lines = text.split("\n")

    # Drop leading preamble + separator noise
    start_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if _is_chatter(line):
            start_idx = i + 1
            continue
        if stripped == "---":
            start_idx = i + 1
            continue
        break
    lines = lines[start_idx:]

    cleaned: list[str] = []
    skip_block = False
    prev_blank = False
    for line in lines:
        # Skip repair gate blocks
        if "Repair Gate" in line or "repair gate" in line.lower():
            skip_block = True
            continue
        if skip_block:
            if line.strip() == "---" or (not line.strip() and cleaned and not cleaned[-1].strip()):
                skip_block = False
            continue
        # Skip file path traces the agents leak
        if _FILE_PATH_RE.match(line) or _HOME_PATH_RE.match(line):
            continue
        if "OUTPUT-REGELN" in line or ("WICHTIG:" in line and "Write-Tool" in line):
            continue
        # Skip chatter anywhere in the document, not just at the top.
        # Also collapse the blank line that typically surrounds it so the
        # final doc doesn't end up with double-empty gaps.
        if _is_chatter(line):
            # If previous line is already blank, don't add another one.
            if cleaned and not cleaned[-1].strip():
                prev_blank = True
            continue
        if not line.strip():
            if prev_blank:
                prev_blank = False
                continue
            prev_blank = True
        else:
            prev_blank = False
        cleaned.append(line)
    return "\n".join(cleaned).strip()
