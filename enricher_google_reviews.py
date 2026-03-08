"""
enricher_google_reviews.py – Holt Google Reviews + Rating via Serper
"""
import re
import time
import json
import logging
import httpx
import sqlite3
from dotenv import load_dotenv
import os

load_dotenv(override=True)
logger = logging.getLogger(__name__)

def get_google_reviews(practice_name: str, city: str, domain: str) -> dict:
    """Holt Google Reviews für eine Praxis via Serper."""
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return {}
    query = f"{practice_name} {city} Zahnarzt"
    if not practice_name or practice_name.strip() == "":
        query = f"{domain} Zahnarzt"
    try:
        resp = httpx.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json={"q": query, "gl": "de", "hl": "de", "num": 3},
            timeout=10,
        )
        data = resp.json()
        # Knowledge Graph (direkte Google Business Info)
        kg = data.get("knowledgeGraph", {})
        if kg:
            rating = kg.get("rating", 0)
            reviews = kg.get("reviewsCount", 0)
            if rating:
                return {"google_rating": float(rating), "google_reviews": int(str(reviews).replace("+", "").replace(",", "").strip() or 0)}

        # Aus organic results
        for result in data.get("organic", []):
            snippet = result.get("snippet", "")
            m_rating = re.search(r'(\d[\.,]\d)\s*(?:von\s*5|★|Sterne|stars)', snippet)
            m_reviews = re.search(r'(\d+(?:\.\d+)?)\s*(?:Bewertungen|reviews|Rezensionen)', snippet)
            if m_rating:
                rating = float(m_rating.group(1).replace(",", "."))
                reviews = int(m_reviews.group(1).replace(".", "")) if m_reviews else 0
                return {"google_rating": rating, "google_reviews": reviews}
    except Exception as e:
        logger.warning(f"Google reviews failed for {domain}: {e}")
    return {}

def compute_review_score(rating: float, count: int) -> int:
    """Berechnet Review Opportunity Score – niedrig = Praxis braucht Hilfe."""
    score = 0
    if count < 20:
        score += 25
    elif count < 50:
        score += 15
    elif count < 100:
        score += 5
    if rating < 4.0:
        score += 20
    elif rating < 4.5:
        score += 10
    elif rating < 4.8:
        score += 5
    return min(score, 40)

def run_google_reviews_enrichment():
    conn = sqlite3.connect("data/leads.db")
    for col in ["google_rating", "google_reviews", "review_opportunity_score"]:
        try:
            conn.execute(f"ALTER TABLE companies ADD COLUMN {col} TEXT")
        except Exception:
            pass
    conn.commit()

    leads = conn.execute(
        "SELECT id, domain, practice_name, city FROM companies WHERE status IN ('scored', 'enriched', 'profiled')"
    ).fetchall()

    print(f"⭐ Google Reviews für {len(leads)} Praxen...")
    for lead_id, domain, name, city in leads:
        data = get_google_reviews(name or "", city or "", domain)
        rating = data.get("google_rating", 0)
        reviews = data.get("google_reviews", 0)
        opp = compute_review_score(rating, reviews)

        conn.execute("""
            UPDATE companies SET
                google_rating = ?,
                google_reviews = ?,
                review_opportunity_score = ?
            WHERE id = ?
        """, (rating, reviews, opp, lead_id))
        conn.commit()

        if rating:
            print(f"  ✓ {domain}: ⭐{rating} ({reviews} Reviews) | Opportunity: {opp}/40")
        else:
            print(f"  - {domain}: keine Reviews gefunden")
        time.sleep(1.5)

    print(f"\n✅ Google Reviews Enrichment abgeschlossen")
    conn.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    run_google_reviews_enrichment()
