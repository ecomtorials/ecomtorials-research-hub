"""Programmatic quality review for research-pipeline.

Shared quality review logic that can be used by both:
- Standalone pipeline (research-pipeline/)
- Web app (ecomtorials-app/)

This module provides deterministic, instant scoring without API calls.
Based on the quality review logic from research-pipeline/pipeline.py step3_quality.
"""
import re
from typing import Optional


# Compiled regex patterns for common checks
_R2_VOC_PATTERN = re.compile(
    r'Kat\.\s*\d|Physical Problem|Emotional Problem|Failed Solution|'
    r'Belief Break|Physical Benefit|Emotional Benefit|Aha-Moment|Wunschzustand',
    re.IGNORECASE,
)
_QUOTE_PATTERN = re.compile(r'"[^"]{20,}"')

# R1 patterns matching _find_missing_categories in pipeline.py
_R1_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [r"Kat\.?\s*\d", r"##+\s*\d", r"Kategorie\s*\d"]
]

# DOI pattern for R3 checks
_DOI_PATTERN = re.compile(r'10\.\d{4,}/[^\s\)]+')


def quality_review(
    r1a: str,
    r1b: str,
    r2_final: str,
    r3_final: str,
    brand: str = "TestBrand",
    threshold: float = 7.0,
) -> dict:
    """Programmatic quality review -- returns scores, issues, and metrics.

    Returns dict with keys:
        qr_r1r2: dict with score + issues
        qr_r3: dict with score + issues
        overall: float
        summary: str
        metrics: dict (7+ metrics)

    Args:
        r1a: R1A content (first part of research)
        r1b: R1B content (second part of research)
        r2_final: R2 VoC research final content
        r3_final: R3 Scientific research final content
        brand: Brand name for product specificity check
        threshold: Minimum score required (default 7.0)
    """
    r1_text = r1a + "\n" + r1b
    r2_text = r2_final
    r3_text = r3_final
    all_text = r1_text + "\n" + r2_text + "\n" + r3_text

    issues_r1r2: list[str] = []
    issues_r3: list[str] = []

    # Q1: Source coverage -- count URLs
    url_count = len(re.findall(r'https?://[^\s\)\]]+', all_text))
    if url_count < 15:
        issues_r1r2.append(f"Nur {url_count} URLs gefunden (min 15 empfohlen)")

    # Q2: Category completeness -- check R1 categories
    r1_cats_found = 0
    for cat_num in range(1, 26):
        if any(p.search(r1_text) for p in _R1_PATTERNS):
            r1_cats_found += 1
    if r1_cats_found < 20:
        issues_r1r2.append(f"Nur {r1_cats_found}/25 R1-Kategorien gefunden (min 20)")

    # Q3: R2 VoC -- check categories present
    r2_cats = len(_R2_VOC_PATTERN.findall(r2_text))
    if r2_cats < 4:
        issues_r1r2.append(f"R2 VoC: nur {r2_cats} Kategorien erkannt (min 6)")

    # Q4: R2 quote count
    quote_count = len(_QUOTE_PATTERN.findall(r2_text))
    if quote_count < 10:
        issues_r1r2.append(f"R2: nur {quote_count} Kundenzitate (min 15 empfohlen)")

    # Q5: R3 DOI count
    doi_count = len(re.findall(_DOI_PATTERN, r3_text))
    if doi_count < 3:
        issues_r3.append(f"R3: nur {doi_count} DOIs (min 5 empfohlen)")

    # Q6: R3 UMP/UMS presence
    has_ump = bool(re.search(r'UMP|Unique Mechanism of Problem', r3_text, re.IGNORECASE))
    has_ums = bool(re.search(r'UMS|Unique Mechanism of Solution', r3_text, re.IGNORECASE))
    if not has_ump:
        issues_r3.append("UMP (Unique Mechanism of Problem) fehlt")
    if not has_ums:
        issues_r3.append("UMS (Unique Mechanism of Solution) fehlt")

    # Q7: Killer-Hooks
    has_hooks = bool(re.search(r'Hook|PARADOX|TABUBRUCH|INDUSTRIE', r3_text, re.IGNORECASE))
    if not has_hooks:
        issues_r3.append("Killer-Hooks fehlen")

    # Q8: Product specificity - brand name should appear frequently
    brand_lower = brand.lower()
    brand_mentions = all_text.lower().count(brand_lower)
    is_product_specific = brand_mentions >= 10
    if not is_product_specific:
        issues_r1r2.append(
            f"Geringe Produktspezifitaet: '{brand}' nur {brand_mentions}x erwaehnt (min 10)"
        )

    # Score calculation
    r1r2_score = 10.0
    if r1_cats_found < 25:
        r1r2_score -= (25 - r1_cats_found) * 0.3
    if r2_cats < 8:
        r1r2_score -= (8 - r2_cats) * 0.3
    if quote_count < 15:
        r1r2_score -= max(0, (15 - quote_count) * 0.1)
    if url_count < 30:
        r1r2_score -= max(0, (30 - url_count) * 0.05)
    if not is_product_specific:
        r1r2_score -= 2.0  # Heavy penalty for generic content
    r1r2_score = max(1.0, min(10.0, round(r1r2_score, 1)))

    r3_score = 10.0
    if doi_count < 5:
        r3_score -= (5 - doi_count) * 0.8
    if not has_ump:
        r3_score -= 2.0
    if not has_ums:
        r3_score -= 2.0
    if not has_hooks:
        r3_score -= 1.0
    r3_score = max(1.0, min(10.0, round(r3_score, 1)))

    overall = round((r1r2_score + r3_score) / 2, 1)

    scores = {
        "qr_r1r2": {"score": r1r2_score, "issues": issues_r1r2},
        "qr_r3": {"score": r3_score, "issues": issues_r3},
        "overall": overall,
        "summary": (
            f"R1: {r1_cats_found}/25 Kategorien, {url_count} URLs. "
            f"R2: {r2_cats} VoC-Kategorien, {quote_count} Zitate. "
            f"R3: {doi_count} DOIs, UMP={'ja' if has_ump else 'nein'}, "
            f"UMS={'ja' if has_ums else 'nein'}, Hooks={'ja' if has_hooks else 'nein'}. "
            f"Produktspezifisch={'ja' if is_product_specific else 'nein'} ({brand_mentions}x '{brand}')."
        ),
        "metrics": {
            "r1_categories": r1_cats_found,
            "url_count": url_count,
            "r2_voc_categories": r2_cats,
            "quote_count": quote_count,
            "doi_count": doi_count,
            "has_ump": has_ump,
            "has_ums": has_ums,
            "has_hooks": has_hooks,
            "brand_mentions": brand_mentions,
            "is_product_specific": is_product_specific,
        },
    }

    # Log if below threshold
    if overall < threshold:
        scores["below_threshold"] = True
        scores["threshold"] = threshold

    return scores


def check_threshold(scores: dict, threshold: float = 7.0) -> bool:
    """Check if quality score meets threshold.

    Args:
        scores: Quality review scores dict from quality_review()
        threshold: Minimum required score

    Returns:
        True if score meets threshold, False otherwise
    """
    return scores["overall"] >= threshold


def get_issues(scores: dict) -> list[str]:
    """Get all issues from quality review scores.

    Args:
        scores: Quality review scores dict from quality_review()

    Returns:
        List of all issue strings
    """
    all_issues = []
    all_issues.extend(scores.get("qr_r1r2", {}).get("issues", []))
    all_issues.extend(scores.get("qr_r3", {}).get("issues", []))
    return all_issues
