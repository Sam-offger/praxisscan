import logging, httpx
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential
from .search_provider_base import BaseSearchProvider, SearchResult
import config

logger = logging.getLogger(__name__)

class SerperProvider(BaseSearchProvider):
    API_URL = "https://google.serper.dev/search"

    def __init__(self):
        if not config.SERPER_API_KEY:
            raise ValueError("SERPER_API_KEY not set in .env")
        self.client = httpx.Client(
            headers={"X-API-KEY": config.SERPER_API_KEY, "Content-Type": "application/json"},
            timeout=15,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        results = []
        try:
            resp = self.client.post(self.API_URL, json={"q": query, "num": num_results, "gl": "de", "hl": "de"})
            resp.raise_for_status()
            for item in resp.json().get("organic", [])[:num_results]:
                results.append(SearchResult(title=item.get("title",""), url=item.get("link",""), snippet=item.get("snippet","")))
        except Exception as e:
            logger.warning(f"Serper search failed: {e}")
        return results
