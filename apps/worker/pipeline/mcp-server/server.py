"""ecomtorials Research Agent — MCP Server.

Provides 8 tools for Claude Code / Claude Desktop:
- 4 Perplexity search presets (fast/pro/deep/academic)
- 2 CrossRef tools (ingredient search + DOI validation)
- 2 PubMed tools (search + fetch abstract)

Orchestration happens via the research-pipeline Skill
which uses Claude Code's built-in Agent tool for subagents.

Usage in .mcp.json:
{
    "ecomtorials-agent": {
        "command": "ecomtorials-research-agent/.venv/Scripts/python",
        "args": ["ecomtorials-research-agent/server.py"],
        "env": {
            "PERPLEXITY_API_KEY": "${PERPLEXITY_API_KEY}"
        }
    }
}
"""

import sys
from pathlib import Path

# Add project root to path so imports work
sys.path.insert(0, str(Path(__file__).parent))

from mcp.server.fastmcp import FastMCP
from tools.perplexity import (
    perplexity_fast_search as _fast,
    perplexity_pro_search as _pro,
    perplexity_deep_research as _deep,
    perplexity_academic_search as _academic,
)
from tools.crossref import (
    crossref_ingredient_search as _crossref_search,
    crossref_validate_doi as _crossref_doi,
)
from tools.pubmed import (
    pubmed_search as _pubmed_search,
    pubmed_fetch_abstract as _pubmed_fetch,
)
from tools.gemini_search import gemini_grounded_search as _gemini_search

mcp = FastMCP("ecomtorials-research")


@mcp.tool()
async def perplexity_fast_search(query: str) -> str:
    """Quick web search via Perplexity (fast preset).
    Best for: current facts, prices, news, quick lookups.
    Response time: fastest. Depth: shallow."""
    return await _fast(query)


@mcp.tool()
async def perplexity_pro_search(query: str) -> str:
    """Standard research via Perplexity (pro preset).
    Best for: standard research, tool comparisons, consumer behavior.
    Response time: moderate. Depth: medium."""
    return await _pro(query)


@mcp.tool()
async def perplexity_deep_research(query: str) -> str:
    """Comprehensive multi-step research via Perplexity (deep preset).
    Best for: market research, competitive analysis, deep-dives.
    Response time: 1-2 minutes. Depth: institutional-grade."""
    return await _deep(query)


@mcp.tool()
async def perplexity_academic_search(query: str) -> str:
    """Academic research using Perplexity Sonar with scholarly domain filter.
    Uses search_mode 'academic' with 22 whitelisted domains (PubMed, Nature, etc.).
    Best for: scientific studies, clinical trials, ingredient research.
    Returns citations with DOI links."""
    return await _academic(query)


@mcp.tool()
async def crossref_ingredient_search(query: str) -> str:
    """Search CrossRef for scientific articles about an ingredient.
    Returns DOI, title, authors, journal, and year for matching articles.
    Use before Perplexity academic_search for pre-validated DOIs."""
    return await _crossref_search(query)


@mcp.tool()
async def crossref_validate_doi(doi: str) -> str:
    """Validate a DOI via CrossRef API.
    Returns metadata if valid, or marks as [DOI-UNVALIDIERT].
    Use to verify DOIs from Perplexity academic_search results."""
    return await _crossref_doi(doi)


@mcp.tool()
async def pubmed_search(query: str, max_results: int = 5) -> str:
    """Search PubMed for scientific articles about an ingredient or topic.
    Automatically translates German INCI names to English.
    Returns title, authors, journal, year, DOI, and abstract summary.
    Best for: medical literature, ingredient mechanisms, clinical evidence."""
    return await _pubmed_search(query, max_results)


@mcp.tool()
async def pubmed_fetch_abstract(pmid: str) -> str:
    """Fetch a single PubMed abstract by PMID and extract its DOI.
    Use to get full abstract + DOI for a known PMID.
    Complements crossref_validate_doi for PMID-based references."""
    return await _pubmed_fetch(pmid)


@mcp.tool()
async def gemini_search(query: str) -> str:
    """Web-Recherche via Gemini Google Search Grounding.
    Liefert Antwort mit Citations und echten URLs.
    Best for: allgemeine Web-Recherche, Marktdaten, Consumer Behavior.
    Requires GEMINI_API_KEY env var."""
    return await _gemini_search(query)


if __name__ == "__main__":
    mcp.run()
