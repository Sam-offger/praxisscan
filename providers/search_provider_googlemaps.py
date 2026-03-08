"""
search_provider_googlemaps.py – Google Maps via SerpAPI free tier.
100 kostenlose Anfragen/Monat. Liefert Bewertungen + Telefon direkt.
Aktivieren: SEARCH_PROVIDER=googlemaps + SERPAPI_API_KEY in .env
"""
import time
import logging
import httpx
from typing import List
from .search_provider_base import BaseSearchProvider, SearchResult
import config

logger = logging.getLogger(__name__)

MAPS_QUERIES = [
    "Zahnarzt Implantate Premium Berlin",
    "Zahnarzt Implantate Premium München",
    "Zahnarzt Veneers Premium Hamburg",
    "Zahnarzt Implantate Premium Frankfurt",
    "Zahnarzt Ästhetik Premium Düsseldorf",
    "Zahnarzt All-on-4 Berlin",
    "Zahnarzt Vollnarkose Premium",
    "Zahnklinik Premium Wien",
    "Zahnarzt Premium Zürich",
]

class GoogleMapsProvider(BaseSearchProvider):
    """
    Nutzt SerpAPI Google Maps Endpoint.
    Kostenlos: 100 Anfragen/Monat auf serpapi.com
    Liefert: Name, Website, Telefon, Rating, Review-Anzahl
    """
    API_URL = "https://serpapi.com/search"

    def __init__(self):
        if not config.SERPAPI_API_KEY:
            raise ValueError("SERPAPI_API_KEY nicht gesetzt. Kostenlos registrieren auf serpapi.com")
        self.client = httpx.Client(timeout=15)

    def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        results = []
        try:
            params = {
                "engine": "google_maps",
                "q": query,
                "hl": "de",
                "gl": "de",
                "api_key": config.SERPAPI_API_KEY,
                "type": "search",
            }
            resp = self.client.get(self.API_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

            for place in data.get("local_results", [])[:num_results]:
                website = place.get("website", "")
                name = place.get("title", "")
                rating = place.get("rating", 0)
                reviews = place.get("reviews", 0)
                phone = place.get("phone", "")
                address = place.get("address", "")

                if not website:
                    continue

                # Snippet mit Review-Daten anreichern
                snippet = f"Rating: {rating} | Reviews: {reviews} | Tel: {phone} | {address}"

                results.append(SearchResult(
                    title=name,
                    url=website,
                    snippet=snippet,
                ))

            logger.info(f"Google Maps: {len(results)} Praxen für '{query}'")
            time.sleep(config.CRAWL_DELAY_S)

        except Exception as e:
            logger.warning(f"Google Maps search failed: {e}")

        return results


class GoogleMapsEnricher:
    """
    Separater Enricher: Holt Reviews + Details für bereits bekannte Domains.
    Nutzt SerpAPI Place Details.
    """
    API_URL = "https://serpapi.com/search"

    def __init__(self):
        if not config.SERPAPI_API_KEY:
            raise ValueError("SERPAPI_API_KEY nicht gesetzt")
        self.client = httpx.Client(timeout=15)

    def get_place_details(self, practice_name: str, city: str) -> dict:
        """Holt Google Maps Details für eine bekannte Praxis."""
        try:
            params = {
                "engine": "google_maps",
                "q": f"{practice_name} Zahnarzt {city}",
                "hl": "de",
                "gl": "de",
                "api_key": config.SERPAPI_API_KEY,
                "type": "search",
            }
            resp = self.client.get(self.API_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

            places = data.get("local_results", [])
            if not places:
                return {}

            place = places[0]
            return {
                "google_rating": place.get("rating", 0),
                "google_reviews": place.get("reviews", 0),
                "google_phone": place.get("phone", ""),
                "google_address": place.get("address", ""),
                "google_hours": place.get("hours", ""),
                "google_place_id": place.get("place_id", ""),
            }
        except Exception as e:
            logger.warning(f"Place details failed for {practice_name}: {e}")
            return {}
