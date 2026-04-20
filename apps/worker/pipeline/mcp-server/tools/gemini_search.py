"""Gemini Google Search Grounding — web search with citations via Gemini API."""

import os
import logging

logger = logging.getLogger(__name__)


async def gemini_grounded_search(query: str, model: str = "gemini-3-flash-preview") -> str:
    """Search the web via Gemini Google Search Grounding.

    Returns Markdown text with inline citations [Title](URL).
    Uses google-genai SDK with Google Search tool.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return "ERROR: GEMINI_API_KEY not set"

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model=model,
            contents=query,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )

        if not response.candidates:
            return f"Keine Ergebnisse fuer: {query}"

        candidate = response.candidates[0]
        text = response.text or ""

        # Extract grounding metadata and add citations
        metadata = getattr(candidate, "grounding_metadata", None)
        if metadata:
            chunks = getattr(metadata, "grounding_chunks", []) or []
            supports = getattr(metadata, "grounding_supports", []) or []

            # Build citation list
            sources = []
            for i, chunk in enumerate(chunks):
                web = getattr(chunk, "web", None)
                if web:
                    uri = getattr(web, "uri", "")
                    title = getattr(web, "title", f"Quelle {i+1}")
                    if uri:
                        sources.append(f"[{title}]({uri})")

            # Insert inline citations
            if supports and chunks:
                sorted_supports = sorted(
                    supports,
                    key=lambda s: getattr(getattr(s, "segment", None), "end_index", 0),
                    reverse=True,
                )
                for support in sorted_supports:
                    indices = getattr(support, "grounding_chunk_indices", []) or []
                    segment = getattr(support, "segment", None)
                    if indices and segment:
                        end_idx = getattr(segment, "end_index", 0)
                        if end_idx and end_idx <= len(text):
                            citation_refs = []
                            for idx in indices:
                                if idx < len(chunks):
                                    web = getattr(chunks[idx], "web", None)
                                    if web and getattr(web, "uri", ""):
                                        citation_refs.append(f"[{idx+1}]")
                            if citation_refs:
                                text = text[:end_idx] + " " + "".join(citation_refs) + text[end_idx:]

            # Append source list at bottom
            if sources:
                text += "\n\n---\n**Quellen:**\n"
                for i, src in enumerate(sources, 1):
                    text += f"{i}. {src}\n"

        return text

    except Exception as e:
        logger.error("Gemini grounded search failed: %s", e)
        return f"Gemini Search Fehler: {e}"
