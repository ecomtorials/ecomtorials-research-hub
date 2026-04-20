"""Jina Reader — URL to clean Markdown via r.jina.ai."""

import logging
import httpx

logger = logging.getLogger(__name__)

JINA_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; EcomtorialsBot/1.0)",
}

async def jina_read(url: str, timeout: int = 30, max_chars: int = 20000) -> tuple[str, bool]:
    """Fetch URL via Jina Reader. Returns (markdown_content, success).

    Primary web scraper — returns clean Markdown instead of raw HTML.
    Free tier: 1M tokens/month, no API key needed.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(
                f"https://r.jina.ai/{url}",
                headers=JINA_HEADERS,
            )
            if resp.status_code != 200:
                logger.warning("Jina returned %d for %s", resp.status_code, url)
                return ("", False)

            data = resp.json()
            content = data.get("data", {}).get("content", "")
            if not content:
                logger.warning("Jina returned empty content for %s", url)
                return ("", False)

            content = content[:max_chars]
            logger.info("Jina scraped %dc from %s", len(content), url)
            return (content, True)
    except Exception as e:
        logger.warning("Jina failed for %s: %s", url, e)
        return ("", False)
