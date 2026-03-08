"""
crawler.py – Polite multi-page website crawler.

For each domain we:
1. Fetch robots.txt (if RESPECT_ROBOTS_TXT=true) and respect disallow rules.
2. Start at the homepage, collect internal links matching PRIORITY_PATHS.
3. Crawl up to MAX_PAGES_PER_DOMAIN pages.
4. Return a dict: {url: html_text}
"""
import re
import time
import logging
import urllib.robotparser
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import config

logger = logging.getLogger(__name__)

# Paths we specifically want to find
PRIORITY_PATH_PATTERNS = [
    r"/kontakt", r"/contact", r"/impressum", r"/imprint",
    r"/team", r"/leistungen", r"/services", r"/preise", r"/pricing",
    r"/karriere", r"/jobs", r"/blog", r"/ueber-uns", r"/about",
    r"/behandlungen", r"/treatments",
]


def _make_client() -> httpx.Client:
    return httpx.Client(
        timeout=config.CRAWL_TIMEOUT_S,
        headers={
            "User-Agent": config.USER_AGENT,
            "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        },
        follow_redirects=True,
    )


def _can_fetch(robot_url: str, url: str) -> bool:
    """Check robots.txt. Returns True if allowed or fetch fails."""
    if not config.RESPECT_ROBOTS_TXT:
        return True
    rp = urllib.robotparser.RobotFileParser()
    try:
        client = _make_client()
        resp = client.get(robot_url, timeout=5)
        rp.parse(resp.text.splitlines())
    except Exception:
        return True  # If robots.txt not accessible, allow
    return rp.can_fetch(config.USER_AGENT, url)


def _is_priority_path(path: str) -> bool:
    path_lower = path.lower()
    for pattern in PRIORITY_PATH_PATTERNS:
        if re.search(pattern, path_lower):
            return True
    return False


def _collect_internal_links(html: str, base_url: str) -> List[str]:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    base_parsed = urlparse(base_url)
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
            continue
        full = urljoin(base_url, href)
        parsed = urlparse(full)
        # Only same domain
        if parsed.netloc == base_parsed.netloc and parsed.scheme in ("http", "https"):
            # Only HTML-like (skip PDFs, images etc.)
            if not re.search(r"\.(pdf|jpg|jpeg|png|gif|svg|css|js|xml|zip)$", parsed.path, re.I):
                links.append(full.split("#")[0])  # strip fragment
    return list(dict.fromkeys(links))  # deduplicate preserving order


@retry(
    stop=stop_after_attempt(config.CRAWL_MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
)
def _fetch(client: httpx.Client, url: str) -> Optional[str]:
    resp = client.get(url)
    resp.raise_for_status()
    ct = resp.headers.get("content-type", "")
    if "text/html" not in ct:
        return None
    return resp.text


def crawl_domain(domain_url: str) -> Dict[str, str]:
    """
    Crawl a domain, returning {url: html_text} for up to MAX_PAGES_PER_DOMAIN pages.
    domain_url should be like: https://example.com
    """
    parsed = urlparse(domain_url)
    if not parsed.scheme:
        domain_url = "https://" + domain_url
        parsed = urlparse(domain_url)

    robot_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    pages: Dict[str, str] = {}
    client = _make_client()

    # We use a priority queue: homepage first, then priority paths, then others
    to_visit_priority: List[str] = [domain_url]
    to_visit_other: List[str] = []
    visited: set = set()

    def _process_url(url: str) -> Optional[str]:
        if url in visited:
            return None
        visited.add(url)
        if not _can_fetch(robot_url, url):
            logger.info(f"  robots.txt disallows: {url}")
            return None
        try:
            html = _fetch(client, url)
            time.sleep(config.CRAWL_DELAY_S)
            return html
        except Exception as e:
            logger.warning(f"  fetch failed {url}: {e}")
            return None

    # Fetch homepage first
    html = _process_url(domain_url)
    if html:
        pages[domain_url] = html
        links = _collect_internal_links(html, domain_url)
        for link in links:
            if _is_priority_path(urlparse(link).path):
                to_visit_priority.append(link)
            else:
                to_visit_other.append(link)

    # Fetch priority paths
    for url in to_visit_priority[1:]:  # skip homepage (already done)
        if len(pages) >= config.MAX_PAGES_PER_DOMAIN:
            break
        html = _process_url(url)
        if html:
            pages[url] = html

    # Fill remaining slots with other pages
    for url in to_visit_other:
        if len(pages) >= config.MAX_PAGES_PER_DOMAIN:
            break
        html = _process_url(url)
        if html:
            pages[url] = html

    logger.info(f"Crawled {len(pages)} pages for {domain_url}")
    return pages
