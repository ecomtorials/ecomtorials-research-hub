"""Programmatic synthesis — merges R1/R2/R3 drafts into final report WITHOUT agents.

Step 2 (R2-Synthesizer) and Step 4 (Assembly) replaced by deterministic Python logic.
No LLM calls, no token cost, instant execution.
"""

import re
from datetime import date
from pathlib import Path


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
        sections.append(r2_raw)
    else:
        sections.append("> ⚠️ R2 VoC-Daten nicht verfuegbar.\n")

    # Extract belief breaks from R1 (Kat. 09) if present
    belief_section = _extract_section(r1a + "\n" + r1b, r"Kat\.?\s*09|Root Cause|Belief Break")
    if belief_section:
        sections.append("\n### 2.2 Belief Breaks (aus R1 Kat. 09)\n")
        sections.append(belief_section)

    # Extract skeptic arguments from R1 (Kat. 20-22)
    skeptic_section = _extract_section(r1b, r"Kat\.?\s*2[012]|Einw[aä]nde|Mythen|Kauf[aä]ngste")
    if skeptic_section:
        sections.append("\n### 2.3 Skeptiker-Argumente + Barrieren (aus R1 Kat. 20-22)\n")
        sections.append(skeptic_section)

    # Extract trigger events from R1 (Kat. 10)
    trigger_section = _extract_section(r1a, r"Kat\.?\s*10|Trigger|Ausl[oö]ser")
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
) -> str:
    """Assemble final Research Report from all components."""
    today = date.today()
    score_r1r2 = scores.get("qr_r1r2", {}).get("score", "?") if scores else "?"
    score_r3 = scores.get("qr_r3", {}).get("score", "?") if scores else "?"
    overall = scores.get("overall", "?") if scores else "?"

    # Count sources
    url_count = len(re.findall(r'https?://[^\s\)]+', r1a + r1b + r2_synthesized + r3_final))
    doi_count = len(re.findall(r'10\.\d{4,}/', r3_final))

    parts = []

    # Header
    parts.append(f"# Research Report: {brand} — {today}\n")
    parts.append(f"**Produkt:** {brand}")
    parts.append(f"**Angle:** {angle}")
    parts.append(f"**Markt:** DACH (primaer Deutschland)")
    parts.append(f"**Erstellt:** {today}")
    parts.append(f"**QR-Scores:** R1/R2: {score_r1r2}/10 | R3: {score_r3}/10 | Gesamt: {overall}/10")
    parts.append(f"**Quellen gesamt:** ~{url_count} URLs, {doi_count} DOIs\n")
    parts.append("---\n")

    # Section 1: Zielgruppenanalyse (R1a + R1b)
    parts.append("## Sektion 1: Zielgruppenanalyse\n")
    if r1a.strip():
        parts.append("### Kategorien 01-13\n")
        parts.append(_clean_agent_output(r1a))
    if r1b.strip():
        parts.append("\n### Kategorien 14-25\n")
        parts.append(_clean_agent_output(r1b))
    parts.append("\n---\n")

    # Section 2: VoC + Belief Architecture (synthesized)
    parts.append(r2_synthesized)
    parts.append("\n---\n")

    # Section 3: Wissenschaftliche Evidenz (R3)
    parts.append(f"## Sektion 3: Wissenschaftliche Evidenz + UMP/UMS — {brand}\n")
    if r3_final.strip():
        parts.append(_clean_agent_output(r3_final))
    else:
        parts.append("> ⚠️ R3 Wissenschaftliche Evidenz nicht verfuegbar.\n")
    parts.append("\n---\n")

    parts.append(f"\n---\n*Research Report erstellt: {today}*\n")

    return "\n".join(parts)


def _extract_section(text: str, pattern: str) -> str:
    """Extract a section from markdown text matching a header pattern."""
    lines = text.split("\n")
    collecting = False
    collected = []
    for line in lines:
        if re.search(pattern, line, re.IGNORECASE):
            collecting = True
            collected.append(line)
        elif collecting:
            # Stop at next major header (## or ###)
            if line.startswith("### Kat") or line.startswith("## "):
                if len(collected) > 2:
                    break
                # If very short section, might be wrong match — continue
                collecting = False
                collected = []
            else:
                collected.append(line)
    return "\n".join(collected).strip()


_PREAMBLE_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r'^Ich habe (jetzt )?alle.*[Dd]aten',
        r'^Jetzt (kompiliere|erstelle|beginne)',
        r'^Hier (ist|sind|kommt)',
        r'^(Gut|Ok|Okay|Alles klar),?\s*(ich|hier|jetzt|lass)',
        r'^Lass mich',
        r'^Ich (werde|beginne|starte)',
        r'^Basierend auf',
    ]
]


def _clean_agent_output(text: str) -> str:
    """Remove agent artifacts like preamble text, repair gate tables, file paths."""
    lines = text.split("\n")

    # Strip preamble: skip matching lines at the top until we hit content
    start_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if any(p.match(stripped) for p in _PREAMBLE_PATTERNS):
            start_idx = i + 1
            continue
        if stripped == "---":
            start_idx = i + 1
            continue
        break
    lines = lines[start_idx:]

    cleaned = []
    skip_block = False
    for line in lines:
        # Skip repair gate check tables
        if "Repair Gate" in line or "repair gate" in line.lower():
            skip_block = True
            continue
        if skip_block:
            if line.strip() == "---" or (not line.strip() and cleaned and not cleaned[-1].strip()):
                skip_block = False
            continue
        # Skip file path references
        if re.match(r'.*R1[ab]?-Draft erstellt:.*', line):
            continue
        if re.match(r'.*`/home/.*\.md`.*', line):
            continue
        # Skip output rules echo
        if "OUTPUT-REGELN" in line or ("WICHTIG:" in line and "Write-Tool" in line):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()
