"""Configuration for the ecomtorials research pipeline.

Standalone version — all paths relative to this directory.
"""

import os
import sys
import importlib.util
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths (standalone — everything under this directory)
# ---------------------------------------------------------------------------
PIPELINE_DIR = Path(__file__).parent
RESEARCH_AGENT_DIR = PIPELINE_DIR / "mcp-server"
RESEARCH_PROMPTS_DIR = PIPELINE_DIR / "research-prompts"
SUBAGENT_PROMPTS_DIR = RESEARCH_AGENT_DIR / "subagent_prompts"
AGENTS_DIR = PIPELINE_DIR / "agents"
EXPORT_SCRIPT = PIPELINE_DIR / "export-docx.mjs"

# ---------------------------------------------------------------------------
# Import constants from mcp-server/config.py (avoid circular import)
# ---------------------------------------------------------------------------
_spec = importlib.util.spec_from_file_location(
    "research_agent_config", RESEARCH_AGENT_DIR / "config.py"
)
_ra_cfg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ra_cfg)

CROSSREF_MAILTO = _ra_cfg.CROSSREF_MAILTO
QUALITY_THRESHOLD = _ra_cfg.QUALITY_THRESHOLD

# ---------------------------------------------------------------------------
# Load .env
# ---------------------------------------------------------------------------
load_dotenv(PIPELINE_DIR / ".env")


def load_config() -> dict:
    """Load pipeline configuration from .env + defaults."""
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    perplexity_key = os.environ.get("PERPLEXITY_API_KEY", "")
    gemini_key = os.environ.get("GEMINI_API_KEY", "")

    if not anthropic_key:
        print("FATAL: ANTHROPIC_API_KEY not set. Copy .env.example to .env and fill in your keys.", file=sys.stderr)
        sys.exit(1)
    if not perplexity_key:
        print("FATAL: PERPLEXITY_API_KEY not set. See .env.example", file=sys.stderr)
        sys.exit(1)
    if not gemini_key:
        print("WARN: GEMINI_API_KEY not set — Gemini Search Grounding disabled.", file=sys.stderr)

    return {
        "anthropic_key": anthropic_key,
        "perplexity_key": perplexity_key,
        "gemini_key": gemini_key,
        "crossref_email": os.environ.get("CROSSREF_EMAIL", CROSSREF_MAILTO),
        "ncbi_api_key": os.environ.get("NCBI_API_KEY", ""),
        "research_model": "claude-sonnet-4-6",
        "scientist_model": "claude-opus-4-6",
        "step0_budget": 0.50,
        "r1_budget": 1.50,
        "r2_budget": 1.00,
        "r3_prefetch_budget": 1.00,
        "r3_scientist_budget": 3.00,
        "step0_turns": 2,
        "r1_turns": 8,
        "r2_turns": 14,
        "r3_prefetch_turns": 12,
        "r3_scientist_turns": 10,
        "quality_threshold": QUALITY_THRESHOLD,
        "repair_r3_budget": 1.50,
        "repair_r1_budget": 0.80,
        "repair_r2_budget": 0.50,
        "repair_turns": 6,
        "max_repair_iterations": 1,
        "deadline_seconds": 2400,
        "use_mcp": True,
    }
