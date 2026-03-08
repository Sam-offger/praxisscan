"""
search_provider_jameda.py – Jameda.de, extrahiert Website + Kontaktdaten aus JS-Config.
"""
import time
import re
import logging
import httpx
from typing import List
from bs4 import BeautifulSoup
from .search_provider_base import BaseSearchProvider, SearchResult
import config

logger = logging.getLogger(__name__)

JAMEDA_CITIES = [
    "berlin", "muenchen", "hamburg", "frankfurt",
    "duesseldorf", "koeln", "stuttgart", "hannover",
    "nuernberg", "dresden",
]

class JamedaProvider(BaseSearchProvider):
    def __init__(self):
        self.client = httpx.Client(
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "de-DE,de;q=0.9",
            },
            follow_redirects=True,
        )

    def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        results = []
        seen = set()

        for city in JAMEDA_CITIES:
            if len(results) >= num_results:
                break
            try:
                url = f"https://www.jameda.de/zahnarzt/{city}"
                resp = self.client.get(url, timeout=15)
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "lxml")

                # Profil-Links extrahieren
                profile_links = []
                for a in soup.find_all("a", href=re.compile(r"jameda\.de/[a-z0-9\-]+/zahnarzt/")):
                    href = a["href"]
                    if "#" in href or href in seen:
                        continue
                    if any(skip in href for skip in ["social-connect", "login", "suche", "javascript"]):
                        continue
                    seen.add(href)
                    profile_links.append(href)

                # Jedes Profil besuchen um Website + Tel zu extrahieren
                for profile_url in profile_links[:3]:
                    try:
                        presult = self._extract_profile(profile_url)
                        if presult:
                            results.append(presult)
                        time.sleep(1)
                    except Exception as e:
                        logger.debug(f"Profile extract failed {profile_url}: {e}")

                time.sleep(config.CRAWL_DELAY_S)

            except Exception as e:
                logger.warning(f"Jameda city {city} failed: {e}")

        logger.info(f"Jameda: {len(results)} Praxen mit Website")
        return results[:num_results]

    def _extract_profile(self, profile_url: str):
        """Besucht ein Jameda-Profil und extrahiert Website + Kontaktdaten."""
        resp = self.client.get(profile_url, timeout=15)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "lxml")
        text = resp.text

        # Arztname aus URL
        parts = profile_url.rstrip("/").split("/")
        doctor_slug = parts[-3] if len(parts) >= 3 else parts[-1]
        city = parts[-1]
        name = doctor_slug.replace("-", " ").title()

        # Website aus externen Links
        website = None
        for a in soup.find_all("a", href=re.compile(r"^https?://(?!.*jameda\.de)")):
            href = a["href"]
            skip = ["google.", "facebook.", "instagram.", "youtube.", "twitter.",
                    "apple.", "noa.ai", "docplanner.", "javascript"]
            if any(s in href for s in skip):
                continue
            if re.search(r"\.(de|at|ch|com|org|net)", href):
                website = href.split("?")[0].rstrip("/")
                break

        # Website aus JS-Config
        if not website:
            m = re.search(r'"website"\s*:\s*"([^"]+)"', text)
            if m:
                website = m.group(1)

        # Rating aus JS oder HTML
        rating = None
        review_count = None
        m = re.search(r'"rating"\s*:\s*([\d.]+)', text)
        if m:
            rating = float(m.group(1))
        m = re.search(r'"reviewsCount"\s*:\s*(\d+)', text)
        if m:
            review_count = int(m.group(1))

        # Telefon aus HTML
        phone = None
        m = re.search(r'tel:([\+\d\s\-\(\)]{7,})', text)
        if m:
            phone = m.group(1).strip()

        if not website:
            return None

        snippet_parts = [f"Jameda: {city.title()}"]
        if rating:
            snippet_parts.append(f"⭐ {rating}")
        if review_count:
            snippet_parts.append(f"{review_count} Reviews")
        if phone:
            snippet_parts.append(f"Tel: {phone}")

        return SearchResult(
            title=f"Dr. {name} – {city.title()}",
            url=website,
            snippet=" | ".join(snippet_parts),
        )
