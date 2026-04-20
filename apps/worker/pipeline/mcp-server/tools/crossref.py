"""CrossRef API functions — ingredient search + DOI validation."""

import urllib.parse
import httpx
from config import CROSSREF_BASE_URL, CROSSREF_MAILTO, CROSSREF_TIMEOUT


async def crossref_ingredient_search(query: str) -> str:
    """Search CrossRef for scientific articles about an ingredient.

    Returns DOI, title, authors, journal, and year for matching journal articles.
    Use before Perplexity academic_search for pre-validated DOIs.
    """
    params = {
        "query": query,
        "filter": "type:journal-article",
        "rows": "3",
        "select": "DOI,title,author,container-title,published-print",
        "mailto": CROSSREF_MAILTO,
    }

    url = f"{CROSSREF_BASE_URL}/works?{urllib.parse.urlencode(params)}"

    async with httpx.AsyncClient(timeout=CROSSREF_TIMEOUT) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    items = data.get("message", {}).get("items", [])
    if not items:
        return f"No CrossRef results for: {query}"

    results = []
    for item in items:
        doi = item.get("DOI", "unknown")
        title_list = item.get("title", [])
        title = title_list[0] if title_list else "No title"
        authors = item.get("author", [])
        author_str = ", ".join(
            f"{a.get('family', '')}, {a.get('given', '')}" for a in authors[:3]
        )
        if len(authors) > 3:
            author_str += " et al."
        journal_list = item.get("container-title", [])
        journal = journal_list[0] if journal_list else "Unknown journal"
        pub = item.get("published-print", {})
        year_parts = pub.get("date-parts", [[]])
        year = year_parts[0][0] if year_parts and year_parts[0] else "n.d."

        results.append(
            f"DOI: https://doi.org/{doi}\n"
            f"Title: {title}\n"
            f"Authors: {author_str}\n"
            f"Journal: {journal}\n"
            f"Year: {year}"
        )

    return "\n\n---\n\n".join(results)


async def crossref_validate_doi(doi: str) -> str:
    """Validate a DOI via CrossRef API.

    Returns metadata if valid, or marks as invalid.
    Use to verify DOIs from Perplexity academic_search results.
    """
    encoded_doi = urllib.parse.quote(doi, safe="")
    url = f"{CROSSREF_BASE_URL}/works/{encoded_doi}"

    async with httpx.AsyncClient(timeout=CROSSREF_TIMEOUT) as client:
        try:
            resp = await client.get(
                url,
                headers={"mailto": CROSSREF_MAILTO},
            )
        except httpx.HTTPError as e:
            return f"[DOI-UNVALIDIERT: {doi}] — Error: {e}"

    if resp.status_code == 200:
        data = resp.json()
        item = data.get("message", {})
        title_list = item.get("title", [])
        title = title_list[0] if title_list else "No title"
        journal_list = item.get("container-title", [])
        journal = journal_list[0] if journal_list else "Unknown"
        authors = item.get("author", [])
        author_str = ", ".join(
            f"{a.get('family', '')}" for a in authors[:3]
        )
        if len(authors) > 3:
            author_str += " et al."
        pub = item.get("published-print", item.get("published-online", {}))
        year_parts = pub.get("date-parts", [[]])
        year = year_parts[0][0] if year_parts and year_parts[0] else "n.d."

        return (
            f"[VALIDIERT] DOI: https://doi.org/{doi}\n"
            f"Title: {title}\n"
            f"Authors: {author_str}\n"
            f"Journal: {journal}\n"
            f"Year: {year}"
        )
    else:
        return f"[DOI-UNVALIDIERT: {doi}] — HTTP {resp.status_code}"
