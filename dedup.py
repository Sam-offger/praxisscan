"""
dedup.py – Deduplication using domain (primary) and fuzzy name+city (secondary).
"""
import logging
import re
from typing import List, Dict, Tuple

from rapidfuzz import fuzz
import tldextract

logger = logging.getLogger(__name__)


def normalize_domain(url: str) -> str:
    """Extract bare domain (e.g. 'zahnarzt-berlin.de') from any URL."""
    ext = tldextract.extract(url)
    if ext.domain and ext.suffix:
        return f"{ext.domain}.{ext.suffix}".lower()
    return url.lower().replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]


def is_duplicate(
    domain: str,
    name: str,
    city: str,
    existing: List[Dict],
    fuzzy_threshold: int = 85,
) -> Tuple[bool, str]:
    """
    Check if a lead is a duplicate.
    Returns (is_dup, reason).
    """
    domain_clean = normalize_domain(domain)

    for existing_lead in existing:
        # Primary: exact domain match
        existing_domain = normalize_domain(existing_lead.get("domain", ""))
        if domain_clean and domain_clean == existing_domain:
            return True, f"domain_match:{existing_domain}"

        # Secondary: fuzzy name + city
        existing_name = existing_lead.get("practice_name", "")
        existing_city = existing_lead.get("city", "")
        if name and existing_name:
            name_score = fuzz.token_sort_ratio(name.lower(), existing_name.lower())
            city_match = city.lower() == existing_city.lower() if city and existing_city else False
            if name_score >= fuzzy_threshold and city_match:
                return True, f"fuzzy_name_city:{name_score}"

    return False, ""


def deduplicate_urls(urls: List[str]) -> List[str]:
    """Remove duplicate URLs (same domain) from a list."""
    seen_domains = set()
    result = []
    for url in urls:
        domain = normalize_domain(url)
        if domain not in seen_domains:
            seen_domains.add(domain)
            result.append(url)
    return result
