"""
score_enhancer.py – Verbessert Scores mit Google Reviews + Preissignalen.
Nutzt SerpAPI/Serper um Google Reviews zu finden.
"""
import json
import re
import time
import logging
import httpx
import sqlite3
from pathlib import Path

import config

logger = logging.getLogger(__name__)

PRICE_PATTERNS = [
    r"ab\s*[\d\.]+\s*€",
    r"[\d\.]+\s*€\s*pro",
    r"preis(?:liste|information)",
    r"investition",
    r"beratungsgespräch",
    r"kostenvoranschlag",
    r"finanzierung",
    r"ratenzahlung",
]

def get_google_reviews(domain: str) -> dict:
    """Sucht Google Reviews für eine Domain via Serper."""
    if not config.SERPER_API_KEY:
        return {"rating": 0, "review_count": 0, "found": False}
    try:
        client = httpx.Client(
            headers={"X-API-KEY": config.SERPER_API_KEY, "Content-Type": "application/json"},
            timeout=10,
        )
        # Praxisname aus Domain ableiten
        query = domain.replace("-", " ").replace(".de", "").replace(".at", "").replace(".ch", "")
        resp = client.post(
            "https://google.serper.dev/search",
            json={"q": f"{query} Zahnarzt Bewertungen", "gl": "de", "hl": "de", "num": 3},
        )
        resp.raise_for_status()
        data = resp.json()

        # Knowledge Graph hat oft Rating
        kg = data.get("knowledgeGraph", {})
        rating = kg.get("rating", 0)
        reviews = kg.get("reviewsCount", 0)

        # Organic results für Review-Signale
        if not rating:
            for result in data.get("organic", []):
                snippet = result.get("snippet", "")
                # Pattern: "4.8 · 127 Rezensionen"
                m = re.search(r"(\d+[.,]\d+)\s*[·•]\s*(\d+)\s*(?:Rezension|Bewertung)", snippet)
                if m:
                    rating = float(m.group(1).replace(",", "."))
                    reviews = int(m.group(2))
                    break

        return {
            "rating": float(rating) if rating else 0,
            "review_count": int(reviews) if reviews else 0,
            "found": bool(rating),
        }
    except Exception as e:
        logger.warning(f"Reviews fetch failed for {domain}: {e}")
        return {"rating": 0, "review_count": 0, "found": False}


def detect_price_signals(text: str) -> dict:
    """Erkennt Preissignale im Website-Text."""
    text_lower = text.lower()
    signals = []
    for pattern in PRICE_PATTERNS:
        if re.search(pattern, text_lower):
            signals.append(pattern)

    # Konkrete Preise extrahieren
    prices = re.findall(r"(\d[\d\.]*)\s*€", text)
    high_prices = [int(p.replace(".", "")) for p in prices
                   if p.replace(".", "").isdigit() and int(p.replace(".", "")) >= 500]

    return {
        "price_signals": signals,
        "high_price_count": len(high_prices),
        "max_price_found": max(high_prices) if high_prices else 0,
    }


def compute_review_bonus(reviews: dict) -> tuple:
    """Berechnet Bonus-Score aus Reviews. Max +15 Punkte."""
    score = 0
    reasons = []

    rating = reviews.get("rating", 0)
    count = reviews.get("review_count", 0)

    # Rating Bonus
    if rating >= 4.8:
        score += 5
        reasons.append(f"exzellentes Rating {rating} (+5)")
    elif rating >= 4.5:
        score += 3
        reasons.append(f"gutes Rating {rating} (+3)")
    elif rating >= 4.0:
        score += 1
        reasons.append(f"Rating {rating} (+1)")

    # Review-Anzahl = Etabliertheit
    if count >= 200:
        score += 5
        reasons.append(f"{count} Reviews – sehr etabliert (+5)")
    elif count >= 100:
        score += 4
        reasons.append(f"{count} Reviews – etabliert (+4)")
    elif count >= 50:
        score += 2
        reasons.append(f"{count} Reviews (+2)")
    elif count >= 20:
        score += 1
        reasons.append(f"{count} Reviews (+1)")

    # Hohe Review-Zahl + gutes Rating = Revenue-Proxy
    if count >= 100 and rating >= 4.5:
        score += 5
        reasons.append("100+ Reviews mit 4.5+ Rating = starker Revenue-Proxy (+5)")

    return min(score, 15), "; ".join(reasons)


def compute_price_bonus(price_data: dict) -> tuple:
    """Berechnet Bonus aus Preissignalen. Max +10 Punkte."""
    score = 0
    reasons = []

    if price_data["high_price_count"] >= 3:
        score += 5
        reasons.append(f"{price_data['high_price_count']} Hochpreisangebote (+5)")
    elif price_data["high_price_count"] >= 1:
        score += 3
        reasons.append(f"{price_data['high_price_count']} Preisangabe 500€+ (+3)")

    if price_data["max_price_found"] >= 5000:
        score += 5
        reasons.append(f"Max. Preis {price_data['max_price_found']}€ – Hochpreis-Segment (+5)")
    elif price_data["max_price_found"] >= 2000:
        score += 3
        reasons.append(f"Max. Preis {price_data['max_price_found']}€ (+3)")

    if price_data["price_signals"]:
        score += 2
        reasons.append("Preisinformationen auf Website (+2)")

    return min(score, 10), "; ".join(reasons)


def enhance_scores():
    """Hauptfunktion: Verbessert alle gescorten Leads."""
    conn = sqlite3.connect("data/leads.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    leads = cursor.execute(
        "SELECT id, domain, total_score, subscores, score_reasons FROM companies WHERE status = 'scored'"
    ).fetchall()

    print(f"\n🔍 Verbessere Scores für {len(leads)} Leads...\n")

    enhanced = 0
    for lead in leads:
        domain = lead["domain"]
        print(f"  Analysiere: {domain}", end=" ")

        # Google Reviews holen
        reviews = get_google_reviews(domain)
        review_bonus, review_reason = compute_review_bonus(reviews)
        time.sleep(1)  # Rate limiting

        # Aktuellen Score laden
        current_score = lead["total_score"] or 0
        try:
            subscores = json.loads(lead["subscores"] or "{}")
            score_reasons = json.loads(lead["score_reasons"] or "{}")
        except Exception:
            subscores = {}
            score_reasons = {}

        # Neuen Score berechnen
        new_score = min(current_score + review_bonus, 100)

        # Subscores updaten
        subscores["google_reviews_bonus"] = review_bonus
        if reviews["found"]:
            subscores["google_rating"] = reviews["rating"]
            subscores["google_review_count"] = reviews["review_count"]

        score_reasons["google_reviews"] = review_reason or "Keine Reviews gefunden"

        # In DB speichern
        cursor.execute("""
            UPDATE companies
            SET total_score = ?,
                subscores = ?,
                score_reasons = ?,
                score_tier = CASE
                    WHEN ? >= 70 THEN 'top'
                    WHEN ? >= 30 THEN 'review'
                    ELSE 'low'
                END
            WHERE id = ?
        """, (
            new_score,
            json.dumps(subscores, ensure_ascii=False),
            json.dumps(score_reasons, ensure_ascii=False),
            new_score, new_score,
            lead["id"]
        ))

        if reviews["found"]:
            print(f"⭐ {reviews['rating']} ({reviews['review_count']} Reviews) → Score: {current_score} → {new_score}")
        else:
            print(f"keine Reviews gefunden → Score bleibt {current_score}")

        enhanced += 1

    conn.commit()
    conn.close()
    print(f"\n✅ {enhanced} Leads verbessert")


if __name__ == "__main__":
    enhance_scores()
