"""
enricher_social.py – Instagram Follower + Google Reviews via Serper
Robuste Version mit mehreren Fallbacks
"""
import re
import time
import logging
import httpx
import sqlite3
import os
from bs4 import BeautifulSoup
from dotenv import load_dotenv
load_dotenv(override=True)

logger = logging.getLogger(__name__)
SERPER_KEY = os.getenv("SERPER_API_KEY")

# ─── Helpers ────────────────────────────────────────────────────────────────

def serper_search(query: str, num: int = 5) -> dict:
    try:
        resp = httpx.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"},
            json={"q": query, "gl": "de", "hl": "de", "num": num},
            timeout=10,
        )
        return resp.json()
    except Exception as e:
        logger.warning(f"Serper failed: {e}")
        return {}

def parse_count(s: str) -> int:
    """Parst Zahlen wie 2.3K+, 73K, 1.2M, 1.234, 1,234"""
    if not s:
        return 0
    s = str(s).strip().replace("\xa0", "").replace(" ", "")
    su = s.upper()
    # K = Tausend
    if "K" in su:
        num = re.sub(r"[^0-9.]", "", su.split("K")[0])
        try:
            return int(float(num) * 1000)
        except:
            pass
    # M = Million
    if "M" in su:
        num = re.sub(r"[^0-9.]", "", su.split("M")[0])
        try:
            return int(float(num) * 1_000_000)
        except:
            pass
    # Normale Zahl
    try:
        return int(re.sub(r"[^\d]", "", s))
    except:
        return 0

JUNK_HANDLES = {
    "p", "reel", "reels", "stories", "explore", "accounts", "share",
    "popular", "trending", "featured", "highlights", "tv", "direct",
    "about", "blog", "help", "press", "api", "legal", "privacy",
    "zahnarzt", "dental", "praxis", "klinik", "clinic",
}

def is_valid_handle(handle: str) -> bool:
    if not handle or len(handle) < 3 or len(handle) > 30:
        return False
    if handle.lower() in JUNK_HANDLES:
        return False
    if re.match(r'^[0-9]+$', handle):
        return False
    return True

# ─── Instagram Handle Finder ────────────────────────────────────────────────

def find_instagram_handle(domain: str) -> str | None:
    """Findet Instagram Handle – Website crawlen + Serper Fallback"""

    # Methode 1: Website direkt crawlen
    for url in [f"https://{domain}", f"https://www.{domain}"]:
        try:
            resp = httpx.get(url, timeout=10,
                headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
                follow_redirects=True)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "lxml")
            # Links
            for a in soup.find_all("a", href=True):
                href = a["href"]
                m = re.search(r'instagram\.com/([a-zA-Z0-9_.]{3,30})/?$', href)
                if m and is_valid_handle(m.group(1)):
                    return m.group(1)
            # Im HTML-Text
            for m in re.finditer(r'instagram\.com/([a-zA-Z0-9_.]{3,30})/?["\'\s\)]', resp.text):
                if is_valid_handle(m.group(1)):
                    return m.group(1)
        except Exception:
            continue

    # Methode 2: Serper – Praxisname + instagram
    clean = re.sub(r'\.(de|at|ch|com|org|berlin|net)$', '', domain)
    clean = clean.replace("-", " ").replace(".", " ")
    for query in [
        f"{clean} zahnarzt instagram",
        f"site:instagram.com {clean} zahnarzt",
    ]:
        try:
            data = serper_search(query)
            for r in data.get("organic", []):
                link = r.get("link", "")
                m = re.search(r'instagram\.com/([a-zA-Z0-9_.]{3,30})/?$', link)
                if m and is_valid_handle(m.group(1)):
                    return m.group(1)
        except Exception:
            pass
        time.sleep(0.5)

    return None

# ─── Instagram Data ──────────────────────────────────────────────────────────

def get_instagram_data(handle: str) -> dict:
    """Holt Follower + Posts via Serper"""
    result = {"followers": 0, "posts": 0, "posts_per_week": 0.0}
    if not handle:
        return result

    FOLLOWER_PATTERNS = [
        r'([\d][.\d]*[KkMm]?\+?)\s*[Ff]ollower',
        r'([\d][.\d]*[KkMm]?\+?)\s*[Aa]bonnenten',
        r'[Ff]ollower[s]?\D{0,5}([\d][.\d]*[KkMm]?\+?)',
    ]
    POST_PATTERNS = [
        r'([\d][.\d]*[KkMm]?)\s*[Pp]ost',
        r'([\d][.\d]*[KkMm]?)\s*[Bb]eitrag',
    ]

    for query in [
        f"{handle} instagram followers",
        f"instagram.com/{handle} followers posts",
    ]:
        try:
            data = serper_search(query)
            for r in data.get("organic", []):
                combined = r.get("snippet", "") + " " + r.get("title", "")
                # Nur wenn der Handle im Text vorkommt
                if handle.lower() not in combined.lower() and "instagram" not in combined.lower():
                    continue
                for p in FOLLOWER_PATTERNS:
                    m = re.search(p, combined, re.IGNORECASE)
                    if m and result["followers"] == 0:
                        result["followers"] = parse_count(m.group(1))
                for p in POST_PATTERNS:
                    m = re.search(p, combined, re.IGNORECASE)
                    if m and result["posts"] == 0:
                        result["posts"] = parse_count(m.group(1))
                if result["followers"] > 0:
                    break
            if result["followers"] > 0:
                break
        except Exception as e:
            logger.warning(f"IG data failed {handle}: {e}")
        time.sleep(0.5)

    if result["posts"] > 0:
        result["posts_per_week"] = round(result["posts"] / (3 * 52), 2)

    return result

# ─── Google Reviews ──────────────────────────────────────────────────────────

def get_google_reviews(practice_name: str, city: str, domain: str) -> dict:
    """Holt Google Rating + Review Count via Serper Maps API"""
    clean_domain = re.sub(r'\.(de|at|ch|com|org|berlin|net)$', '', domain)
    clean_domain = clean_domain.replace("-", " ")

    queries = [
        f"{practice_name} {city}",
        f"{clean_domain} Zahnarzt {city}",
        f"{clean_domain} Zahnarzt",
    ]

    for query in queries:
        try:
            resp = httpx.post(
                "https://google.serper.dev/maps",
                headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"},
                json={"q": query, "gl": "de", "hl": "de"},
                timeout=10,
            )
            data = resp.json()
            places = data.get("places", [])

            for place in places:
                website = place.get("website", "")
                # Prüfen ob die Website zur Domain passt
                if domain in website or clean_domain.replace(" ", "-") in website:
                    rating = float(place.get("rating", 0))
                    count = parse_count(str(place.get("ratingCount", 0)))
                    if rating > 0:
                        return {"rating": rating, "reviews": count}

            # Fallback: ersten Treffer nehmen wenn Name passt
            for place in places[:2]:
                title = place.get("title", "").lower()
                if any(w in title for w in clean_domain.lower().split() if len(w) > 3):
                    rating = float(place.get("rating", 0))
                    count = parse_count(str(place.get("ratingCount", 0)))
                    if rating > 0:
                        return {"rating": rating, "reviews": count}

            time.sleep(0.5)
        except Exception as e:
            logger.warning(f"Maps reviews failed {domain}: {e}")

    return {}

# ─── Main ────────────────────────────────────────────────────────────────────

def run_social_enrichment(limit: int = None):
    conn = sqlite3.connect("data/leads.db")
    for col_def in [
        "instagram_posts INTEGER DEFAULT 0",
        "instagram_posts_per_week REAL DEFAULT 0",
    ]:
        try:
            conn.execute(f"ALTER TABLE companies ADD COLUMN {col_def}")
        except Exception:
            pass
    conn.commit()

    query = """
        SELECT id, domain, practice_name, city
        FROM companies WHERE status IN ('scored', 'enriched', 'profiled')
        ORDER BY opportunity_score DESC
    """
    if limit:
        query += f" LIMIT {limit}"

    leads = conn.execute(query).fetchall()
    print(f"📱 Social + Reviews Enrichment für {len(leads)} Leads...\n")

    for lead_id, domain, name, city in leads:
        print(f"🔍 {domain}")

        handle = find_instagram_handle(domain)
        time.sleep(1)

        ig = get_instagram_data(handle) if handle else {}
        time.sleep(1.5)

        reviews = get_google_reviews(name or "", city or "", domain)
        time.sleep(1.5)

        conn.execute("""
            UPDATE companies SET
                instagram_handle = ?,
                instagram_followers = ?,
                instagram_posts = ?,
                instagram_posts_per_week = ?,
                google_rating = ?,
                google_reviews = ?
            WHERE id = ?
        """, (
            handle or "",
            ig.get("followers", 0),
            ig.get("posts", 0),
            ig.get("posts_per_week", 0.0),
            reviews.get("rating", 0),
            reviews.get("reviews", 0),
            lead_id,
        ))
        conn.commit()

        ig_str = f"@{handle} | {ig.get('followers',0)} followers | {ig.get('posts_per_week',0)} posts/week" if handle else "❌ kein Instagram"
        review_str = f"⭐{reviews.get('rating',0)} ({reviews.get('reviews',0)} Reviews)" if reviews.get("rating") else "❌ keine Reviews"
        print(f"  Instagram: {ig_str}")
        print(f"  Google:    {review_str}\n")

    print("✅ Fertig – jetzt opportunity_scorer.py laufen lassen")
    conn.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    run_social_enrichment()
