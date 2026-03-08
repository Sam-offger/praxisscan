"""
enricher_owner.py – Extrahiert Inhaber/Arztname aus Website + Impressum
"""
import re
import logging
import httpx
from bs4 import BeautifulSoup
import sqlite3

logger = logging.getLogger(__name__)

OWNER_PATTERNS = [
    r'(?:Dr\.?|Prof\.?|Dr\.-Ing\.?)\s+[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+){1,3}',
    r'(?:Inhaber|Praxisinhaber|Leitung|Gründer)[\s:]+([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+){1,3})',
    r'(?:Ihr\s+(?:Zahnarzt|Arzt|Spezialist))[\s:]+(?:Dr\.?\s+)?([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+){1,2})',
]

def extract_owner(domain: str) -> str | None:
    urls = [
        f"https://{domain}/impressum",
        f"https://{domain}/impressum.html",
        f"https://{domain}/ueber-uns",
        f"https://{domain}/about",
        f"https://{domain}",
    ]
    client = httpx.Client(
        timeout=10,
        headers={"User-Agent": "Mozilla/5.0"},
        follow_redirects=True,
    )
    for url in urls:
        try:
            resp = client.get(url, timeout=10)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "lxml")
            text = soup.get_text(" ", strip=True)
            for pattern in OWNER_PATTERNS:
                matches = re.findall(pattern, text)
                if matches:
                    name = matches[0] if isinstance(matches[0], str) else matches[0][0]
                    name = name.strip()
                    if 5 < len(name) < 60:
                        logger.info(f"Owner found for {domain}: {name}")
                        return name
        except Exception:
            continue
    return None

def run_owner_enrichment():
    conn = sqlite3.connect("data/leads.db")
    leads = conn.execute(
        "SELECT id, domain FROM companies WHERE status IN ('scored', 'enriched', 'profiled') AND (owner_name IS NULL OR owner_name = '')"
    ).fetchall()

    print(f"🔍 Suche Inhaber für {len(leads)} Praxen...")
    found = 0
    for lead_id, domain in leads:
        name = extract_owner(domain)
        if name:
            conn.execute("UPDATE companies SET owner_name = ? WHERE id = ?", (name, lead_id))
            conn.commit()
            found += 1
            print(f"  ✓ {domain}: {name}")
        else:
            print(f"  - {domain}: nicht gefunden")

    print(f"\n✅ {found}/{len(leads)} Inhaber gefunden")
    conn.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    run_owner_enrichment()
