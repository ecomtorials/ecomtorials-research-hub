"""Prompt loader — reads existing .md prompt files and injects variables."""

from pathlib import Path

from config import (
    AGENTS_DIR,
    RESEARCH_PROMPTS_DIR,
    SUBAGENT_PROMPTS_DIR,
)

# ---------------------------------------------------------------------------
# Prompt cache (file-level, avoids re-reading within one pipeline run)
# ---------------------------------------------------------------------------
_cache: dict[str, str] = {}


def _load(path: Path) -> str:
    """Read a prompt file, cached."""
    key = str(path)
    if key not in _cache:
        if not path.exists():
            raise FileNotFoundError(f"Prompt not found: {path}")
        _cache[key] = path.read_text(encoding="utf-8")
    return _cache[key]


def inject_variables(text: str, variables: dict[str, str]) -> str:
    """Replace {VAR_NAME} placeholders in prompt text."""
    for k, v in variables.items():
        text = text.replace(f"{{{k}}}", str(v))
    return text


# ---------------------------------------------------------------------------
# Research prompts
# ---------------------------------------------------------------------------

def load_r1_prompt() -> str:
    return _load(RESEARCH_PROMPTS_DIR / "R1-zielgruppen-research.md")


def load_r2_prompt() -> str:
    return _load(RESEARCH_PROMPTS_DIR / "R2-sprachanalyse.md")


def load_r3_prompt() -> str:
    return _load(RESEARCH_PROMPTS_DIR / "R3-ump-ums-research.md")


def load_source_rules() -> str:
    return _load(RESEARCH_PROMPTS_DIR / "source-rules.md")


# ---------------------------------------------------------------------------
# Subagent prompts (from research-agent)
# ---------------------------------------------------------------------------

def load_subagent_prompt(name: str) -> str:
    """Load a subagent prompt by filename (without .md extension)."""
    return _load(SUBAGENT_PROMPTS_DIR / f"{name}.md")


def load_shared_rules(name: str) -> str:
    """Load a shared rules file from subagent_prompts/shared/."""
    return _load(SUBAGENT_PROMPTS_DIR / "shared" / f"{name}.md")


# ---------------------------------------------------------------------------
# Quality reviewer
# ---------------------------------------------------------------------------

def load_quality_reviewer() -> str:
    return _load(AGENTS_DIR / "research-quality-reviewer.md")


# ---------------------------------------------------------------------------
# Composite prompts (combine base + rules + variables)
# ---------------------------------------------------------------------------

def build_r1_system_prompt(category_range: str, variables: dict[str, str]) -> str:
    """Build R1 researcher system prompt for a category range (e.g., '01-13')."""
    base = load_subagent_prompt("r1_researcher")
    source_rules = load_source_rules()
    try:
        shared_mins = load_shared_rules("category_minimums")
    except FileNotFoundError:
        shared_mins = ""

    prompt = f"""# Quellen-Regeln
{source_rules}

# Kategorie-Minimums
{shared_mins}

# Aufgabe
{base}

# Dein Bereich: Kategorien {category_range}
Recherchiere NUR die Kategorien {category_range}. Ignoriere alle anderen.
"""
    return inject_variables(prompt, variables)


def build_r2_system_prompt(variables: dict[str, str]) -> str:
    """Build R2 VoC collector system prompt."""
    base = load_subagent_prompt("r2_voc_collector")
    source_rules = load_source_rules()
    prompt = f"""# Quellen-Regeln
{source_rules}

# Aufgabe
{base}
"""
    return inject_variables(prompt, variables)


def build_r3_prefetch_system_prompt(variables: dict[str, str]) -> str:
    """Build R3 CrossRef prefetch system prompt."""
    base = load_subagent_prompt("r3_crossref_prefetch")
    prompt = f"""# Aufgabe
{base}
"""
    return inject_variables(prompt, variables)


def build_r2_synthesizer_system_prompt(variables: dict[str, str]) -> str:
    """Build R2 synthesizer system prompt."""
    base = load_subagent_prompt("r2_synthesizer")
    return inject_variables(base, variables)


def build_r3_scientist_system_prompt(variables: dict[str, str]) -> str:
    """Build R3 scientist system prompt."""
    base = load_subagent_prompt("r3_scientist")
    source_rules = load_source_rules()
    prompt = f"""# Quellen-Regeln
{source_rules}

# Aufgabe
{base}
"""
    return inject_variables(prompt, variables)


def build_qr_system_prompt() -> str:
    """Build Quality Reviewer system prompt."""
    return load_quality_reviewer()


def build_assembly_system_prompt(variables: dict[str, str]) -> str:
    """Build assembler system prompt."""
    base = load_subagent_prompt("assembler")
    return inject_variables(base, variables)
