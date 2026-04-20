"""Perplexity API functions — 4 presets (fast/pro/deep/academic).

Uses the Agent API (POST /v1/agent) for preset-based searches (fast/pro/deep).
Uses the Chat Completions API for academic_search (search_mode: "academic").

Agent API presets provide multi-step reasoning with web_search + fetch_url tools:
  - fast-search:  xai/grok-4-1-fast, 1 step,  web_search only
  - pro-search:   openai/gpt-5.1,    3 steps, web_search + fetch_url
  - deep-research: openai/gpt-5.2,   10 steps, web_search + fetch_url

Custom parameters (reasoning, tools, instructions) override preset defaults
while preserving other optimized preset configurations.
"""

import os
import random
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

import anyio
import httpx
from config import (
    ACADEMIC_DOMAINS,
    PERPLEXITY_AGENT_URL,
    PERPLEXITY_CHAT_URL,
    PERPLEXITY_BLOCKED_DOMAINS,
    PERPLEXITY_INSTRUCTIONS,
)

_TIMEOUT = 180  # seconds — deep-research can take 1-2 min, buffer extra
_MAX_RETRIES = 4


def _get_api_key() -> str:
    key = os.environ.get("PERPLEXITY_API_KEY", "")
    if not key:
        raise RuntimeError("PERPLEXITY_API_KEY is not set")
    return key


def _parse_retry_after(header_value: str | None, default: float) -> float:
    """Parse Retry-After header (seconds integer or HTTP-date). Fall back to default."""
    if not header_value:
        return default
    stripped = header_value.strip()
    try:
        return max(0.0, float(stripped))
    except ValueError:
        pass
    try:
        dt = parsedate_to_datetime(stripped)
        if dt is None:
            return default
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = (dt - datetime.now(timezone.utc)).total_seconds()
        return max(0.0, delta)
    except (TypeError, ValueError):
        return default


async def _http_post_with_retry(
    url: str,
    *,
    headers: dict,
    json: dict,
    max_retries: int = _MAX_RETRIES,
) -> httpx.Response:
    """POST with retry+exponential backoff+jitter on 429/5xx/ReadTimeout.

    Each attempt uses a fresh httpx.AsyncClient so a ReadTimeout does not poison
    the connection pool. Every MCP subprocess retries independently, which is
    the only viable cross-process rate-limit strategy (asyncio.Semaphore can't
    span subprocesses).
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(url, headers=headers, json=json)
            if resp.status_code == 429:
                if attempt == max_retries - 1:
                    resp.raise_for_status()
                delay = _parse_retry_after(
                    resp.headers.get("Retry-After"),
                    default=(2 ** attempt) + random.random(),
                )
                await anyio.sleep(delay)
                continue
            if 500 <= resp.status_code < 600 and attempt < max_retries - 1:
                await anyio.sleep(2 + random.random())
                continue
            resp.raise_for_status()
            return resp
        except httpx.ReadTimeout as exc:
            last_exc = exc
            if attempt == max_retries - 1:
                raise
            continue
    raise RuntimeError(
        f"Perplexity: {max_retries} retries exhausted"
    ) from last_exc


async def perplexity_fast_search(query: str) -> str:
    """Quick web search via Perplexity Agent API (fast-search preset).

    Best for: current facts, prices, news, quick lookups.
    Uses: xai/grok-4-1-fast, 1 reasoning step, web_search only.
    """
    return await _run_preset("fast-search", query)


async def perplexity_pro_search(query: str) -> str:
    """Standard research via Perplexity Agent API (pro-search preset).

    Best for: standard research, tool comparisons, consumer behavior.
    Uses: openai/gpt-5.1, 3 reasoning steps, web_search + fetch_url.
    """
    return await _run_preset("pro-search", query)


async def perplexity_deep_research(query: str) -> str:
    """Comprehensive multi-step research via Perplexity Agent API (deep-research preset).

    Best for: market research, competitive analysis, deep-dives.
    Uses: openai/gpt-5.2, 10 reasoning steps, web_search + fetch_url.
    Response time: 1-2 minutes.
    """
    return await _run_preset("deep-research", query)


async def perplexity_academic_search(query: str) -> str:
    """Academic research using Perplexity Sonar with scholarly domain filter.

    Uses Chat Completions API with search_mode 'academic' and 22 whitelisted domains.
    Best for: scientific studies, clinical trials, peer-reviewed papers.
    Returns citations with DOI links.
    """
    api_key = _get_api_key()

    payload = {
        "model": "sonar-pro",
        "messages": [{"role": "user", "content": query}],
        "search_mode": "academic",
        "search_domain_filter": ACADEMIC_DOMAINS,
        "search_language_filter": ["de", "en"],
        "web_search_options": {"search_context_size": "high"},
    }

    resp = await _http_post_with_retry(
        PERPLEXITY_CHAT_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
    )
    data = resp.json()

    content = ""
    choices = data.get("choices", [])
    if choices:
        content = choices[0].get("message", {}).get("content", "")

    citations = data.get("citations", [])
    if citations:
        citation_block = "\n\n---\nQuellen:\n" + "\n".join(
            f"[{i + 1}] {c}" for i, c in enumerate(citations)
        )
        content += citation_block

    return content


async def _run_preset(preset: str, query: str) -> str:
    """Call Perplexity Agent API with a preset + custom parameter overrides.

    Custom parameters override preset defaults while keeping other preset
    configurations (model, system prompt, step limits) intact.

    Parameters added per Perplexity Agent API docs:
    - reasoning.effort: controls reasoning depth
    - tools: explicit web_search with domain denylist + fetch_url
    - instructions: German language + source quality guidance
    """
    api_key = _get_api_key()

    # Base payload — custom params override preset defaults
    payload = {
        "preset": preset,
        "input": query,
        "reasoning": {"effort": "medium"},
        "tools": [
            {
                "type": "web_search",
                "filters": {
                    "search_domain_filter": PERPLEXITY_BLOCKED_DOMAINS,
                },
            },
            {"type": "fetch_url"},
        ],
        "instructions": PERPLEXITY_INSTRUCTIONS,
    }

    # Preset-specific overrides
    if preset == "deep-research":
        payload["reasoning"] = {"effort": "high"}
        payload["max_output_tokens"] = 10000

    elif preset == "fast-search":
        # fast-search: no reasoning, no fetch_url — keep it fast
        payload["tools"] = [
            {
                "type": "web_search",
                "filters": {
                    "search_domain_filter": PERPLEXITY_BLOCKED_DOMAINS,
                },
            },
        ]
        del payload["reasoning"]

    resp = await _http_post_with_retry(
        PERPLEXITY_AGENT_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
    )
    data = resp.json()

    # Extract text and search results from Agent API response
    text_parts = []
    sources = []

    for item in data.get("output", []):
        item_type = item.get("type", "")

        if item_type == "message":
            for block in item.get("content", []):
                if block.get("type") == "output_text":
                    text_parts.append(block.get("text", ""))

        elif item_type == "search_results":
            for result in item.get("results", []):
                url = result.get("url", "")
                title = result.get("title", "")
                if url:
                    sources.append({"url": url, "title": title})

    content = "\n".join(text_parts)

    # Append sources as citation block
    if sources:
        seen = set()
        unique_sources = []
        for s in sources:
            if s["url"] not in seen:
                seen.add(s["url"])
                unique_sources.append(s)
        citation_block = "\n\n---\nQuellen:\n" + "\n".join(
            f"[{i + 1}] {s['title']} — {s['url']}" if s["title"] else f"[{i + 1}] {s['url']}"
            for i, s in enumerate(unique_sources)
        )
        content += citation_block

    return content
