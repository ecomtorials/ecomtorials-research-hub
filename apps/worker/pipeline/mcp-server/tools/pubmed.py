"""PubMed E-Utilities API — ESearch + EFetch for medical literature.

Provides direct access to NCBI PubMed for ingredient research.
Complements CrossRef (which finds articles) by delivering full abstracts
and reliable DOI extraction from PubMed's ArticleIdList.

Free API — no authentication required (respects 3 req/sec limit).
"""

import httpx
import xml.etree.ElementTree as ET

_TIMEOUT = 30
_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# Common INCI German → English mappings for automatic query translation
_INCI_TRANSLATIONS = {
    "rindertalg": "beef tallow",
    "sheabutter": "shea butter",
    "jojobaöl": "jojoba oil",
    "arganöl": "argan oil",
    "rizinusöl": "castor oil",
    "kokosöl": "coconut oil",
    "olivenöl": "olive oil",
    "hyaluronsäure": "hyaluronic acid",
    "retinol": "retinol",
    "vitamin c": "ascorbic acid",
    "vitamin e": "tocopherol",
    "niacinamid": "niacinamide",
    "zink": "zinc",
    "magnesium": "magnesium",
    "kollagen": "collagen",
    "ceramide": "ceramides",
    "panthenol": "panthenol",
    "bisabolol": "bisabolol",
    "allantoin": "allantoin",
    "urea": "urea",
    "salicylsäure": "salicylic acid",
    "glykolsäure": "glycolic acid",
    "milchsäure": "lactic acid",
    "squalan": "squalane",
    "peptide": "peptides",
    "probiotika": "probiotics",
    "präbiotika": "prebiotics",
    "kurkuma": "curcumin",
    "grüner tee": "green tea extract",
    "aloe vera": "aloe vera",
    "teebaumöl": "tea tree oil",
    "hanföl": "hemp seed oil",
    "traubenkernöl": "grape seed oil",
    "rosmarinextrakt": "rosemary extract",
    "koffein": "caffeine",
    "bakuchiol": "bakuchiol",
    "azelainsäure": "azelaic acid",
}


def _translate_query(query: str) -> str:
    """Translate German INCI terms to English for better PubMed results."""
    lower = query.lower()
    for de, en in _INCI_TRANSLATIONS.items():
        if de in lower:
            lower = lower.replace(de, en)
    return lower


def _parse_article(article: ET.Element) -> dict:
    """Extract structured data from a PubMed XML article."""
    result = {
        "pmid": "",
        "title": "",
        "authors": "",
        "journal": "",
        "year": "",
        "doi": "",
        "abstract": "",
    }

    # PMID
    pmid_el = article.find(".//PMID")
    if pmid_el is not None and pmid_el.text:
        result["pmid"] = pmid_el.text

    # Title
    title_el = article.find(".//ArticleTitle")
    if title_el is not None:
        result["title"] = "".join(title_el.itertext()).strip()

    # Authors (first 3 + et al.)
    authors = []
    for author in article.findall(".//Author"):
        last = author.findtext("LastName", "")
        initials = author.findtext("Initials", "")
        if last:
            authors.append(f"{last} {initials}".strip())
    if len(authors) > 3:
        result["authors"] = ", ".join(authors[:3]) + " et al."
    elif authors:
        result["authors"] = ", ".join(authors)

    # Journal
    journal_el = article.find(".//Journal/Title")
    if journal_el is not None and journal_el.text:
        result["journal"] = journal_el.text

    # Year
    year_el = article.find(".//PubDate/Year")
    if year_el is not None and year_el.text:
        result["year"] = year_el.text
    else:
        medline_year = article.find(".//MedlineDate")
        if medline_year is not None and medline_year.text:
            result["year"] = medline_year.text[:4]

    # DOI from ArticleIdList
    for article_id in article.findall(".//ArticleId"):
        if article_id.get("IdType") == "doi" and article_id.text:
            result["doi"] = article_id.text
            break

    # Abstract
    abstract_parts = []
    for abstract_text in article.findall(".//AbstractText"):
        label = abstract_text.get("Label", "")
        text = "".join(abstract_text.itertext()).strip()
        if label and text:
            abstract_parts.append(f"{label}: {text}")
        elif text:
            abstract_parts.append(text)
    result["abstract"] = " ".join(abstract_parts)

    return result


def _format_article(article: dict) -> str:
    """Format a parsed article into readable output."""
    lines = []
    lines.append(f"Title: {article['title']}")
    if article["authors"]:
        lines.append(f"Authors: {article['authors']}")
    if article["journal"]:
        lines.append(f"Journal: {article['journal']}")
    if article["year"]:
        lines.append(f"Year: {article['year']}")
    if article["doi"]:
        lines.append(f"DOI: https://doi.org/{article['doi']}")
    lines.append(f"PMID: {article['pmid']}")
    if article["abstract"]:
        # Truncate long abstracts to ~500 chars
        abstract = article["abstract"]
        if len(abstract) > 500:
            abstract = abstract[:497] + "..."
        lines.append(f"Abstract: {abstract}")
    return "\n".join(lines)


async def pubmed_search(query: str, max_results: int = 5) -> str:
    """Search PubMed for scientific articles about an ingredient or topic.

    Automatically translates German INCI names to English for better results.
    Returns title, authors, journal, year, DOI, and abstract summary.

    Args:
        query: Search term (e.g., "retinol skin barrier" or "Hyaluronsäure Hautalterung")
        max_results: Maximum number of results (1-10, default 5)
    """
    max_results = max(1, min(10, max_results))
    translated = _translate_query(query)

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        # Step 1: ESearch — get PMIDs
        search_resp = await client.get(
            _ESEARCH_URL,
            params={
                "db": "pubmed",
                "term": translated,
                "retmax": max_results,
                "retmode": "json",
                "sort": "relevance",
            },
        )
        search_resp.raise_for_status()
        search_data = search_resp.json()

        id_list = search_data.get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return f"Keine PubMed-Ergebnisse für: {query} (übersetzt: {translated})"

        # Step 2: EFetch — get article details
        fetch_resp = await client.get(
            _EFETCH_URL,
            params={
                "db": "pubmed",
                "id": ",".join(id_list),
                "rettype": "abstract",
                "retmode": "xml",
            },
        )
        fetch_resp.raise_for_status()

    # Parse XML
    root = ET.fromstring(fetch_resp.text)
    articles = root.findall(".//PubmedArticle")

    if not articles:
        return f"PubMed EFetch lieferte keine Artikel für IDs: {', '.join(id_list)}"

    results = []
    for article_el in articles:
        parsed = _parse_article(article_el)
        results.append(_format_article(parsed))

    header = f"PubMed-Ergebnisse für: {query}"
    if translated.lower() != query.lower():
        header += f" (übersetzt: {translated})"
    header += f"\n{len(results)} Artikel gefunden:\n"

    return header + "\n\n---\n\n".join(results)


async def pubmed_fetch_abstract(pmid: str) -> str:
    """Fetch a single PubMed abstract by PMID and extract its DOI.

    Use this to get the full abstract and DOI for a known PMID.

    Args:
        pmid: PubMed ID (e.g., "12345678")
    """
    pmid = pmid.strip()

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(
            _EFETCH_URL,
            params={
                "db": "pubmed",
                "id": pmid,
                "rettype": "abstract",
                "retmode": "xml",
            },
        )
        resp.raise_for_status()

    root = ET.fromstring(resp.text)
    articles = root.findall(".//PubmedArticle")

    if not articles:
        return f"Kein Artikel gefunden für PMID: {pmid}"

    parsed = _parse_article(articles[0])
    return _format_article(parsed)
