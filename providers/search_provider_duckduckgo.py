import time, re, logging, httpx
from typing import List
from .search_provider_base import BaseSearchProvider, SearchResult
import config

logger = logging.getLogger(__name__)

class DuckDuckGoProvider(BaseSearchProvider):

    def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        results = []
        try:
            # Schritt 1: Session + Cookie holen
            client = httpx.Client(
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
                },
                follow_redirects=True,
            )
            # Erst Homepage besuchen um Cookie zu bekommen
            client.get("https://duckduckgo.com/", timeout=10)
            time.sleep(1)

            # Schritt 2: Lite-Version mit vqd Token
            resp = client.post(
                "https://html.duckduckgo.com/html/",
                data={"q": query, "b": "", "kl": "de-de", "df": ""},
                headers={"Referer": "https://duckduckgo.com/"},
                timeout=15,
            )

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "lxml")

            # Neue Selektoren (DDG ändert diese regelmäßig)
            for div in soup.find_all("div", class_=re.compile(r"result", re.I))[:num_results * 2]:
                a = div.find("a", class_=re.compile(r"result__a|result-link", re.I))
                if not a:
                    a = div.find("a", href=re.compile(r"^https?://"))
                if not a:
                    continue
                href = a.get("href", "")
                url = self._extract_url(href)
                if not url or not url.startswith("http"):
                    continue
                # Filter DDG-interne Links
                if "duckduckgo.com" in url:
                    continue
                title = a.get_text(strip=True)
                snippet_tag = div.find(class_=re.compile(r"snippet|result__snippet", re.I))
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
                if url and title:
                    results.append(SearchResult(title=title, url=url, snippet=snippet))
                if len(results) >= num_results:
                    break

            if not results:
                # Fallback: alle externen Links auf der Seite
                for a in soup.find_all("a", href=re.compile(r"^https?://")):
                    href = a.get("href", "")
                    if "duckduckgo.com" in href or "duck.com" in href:
                        continue
                    title = a.get_text(strip=True)
                    if len(title) > 10:
                        results.append(SearchResult(title=title, url=href, snippet=""))
                    if len(results) >= num_results:
                        break

            logger.info(f"DDG found {len(results)} results for: {query}")
            time.sleep(config.CRAWL_DELAY_S)

        except Exception as e:
            logger.warning(f"DDG search failed for '{query}': {e}")
        return results

    @staticmethod
    def _extract_url(raw: str) -> str:
        m = re.search(r"uddg=([^&]+)", raw)
        if m:
            from urllib.parse import unquote
            return unquote(m.group(1))
        return raw if raw.startswith("http") else ""
