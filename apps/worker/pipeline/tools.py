"""Tool configuration — MCP server setup for research agents."""

import os
import sys
from pathlib import Path

from config import RESEARCH_AGENT_DIR


def build_mcp_servers(cfg: dict) -> dict | None:
    """Build MCP server config for ClaudeAgentOptions.

    Uses the existing ecomtorials-research-agent FastMCP server which provides
    8 tools: perplexity_fast_search, perplexity_pro_search, perplexity_deep_research,
    perplexity_academic_search, crossref_ingredient_search, crossref_validate_doi,
    pubmed_search, pubmed_fetch_abstract.
    """
    if not cfg.get("use_mcp", True):
        return None

    server_path = RESEARCH_AGENT_DIR / "server.py"
    if not server_path.exists():
        print(
            f"[WARN] MCP server not found at {server_path}, using WebSearch fallback",
            file=sys.stderr,
        )
        return None

    # Find Python interpreter — prefer venv if exists
    venv_python = RESEARCH_AGENT_DIR / ".venv" / "bin" / "python"
    python_cmd = str(venv_python) if venv_python.exists() else "python3"

    env = {}
    if cfg.get("perplexity_key"):
        env["PERPLEXITY_API_KEY"] = cfg["perplexity_key"]
    if cfg.get("gemini_key"):
        env["GEMINI_API_KEY"] = cfg["gemini_key"]
    if cfg.get("ncbi_api_key"):
        env["NCBI_API_KEY"] = cfg["ncbi_api_key"]
    if cfg.get("crossref_email"):
        env["CROSSREF_EMAIL"] = cfg["crossref_email"]

    return {
        "ecomtorials-research": {
            "command": python_cmd,
            "args": [str(server_path)],
            "env": env,
            "cwd": str(RESEARCH_AGENT_DIR),
        }
    }


