"""
opportunity_scorer.py – Berechnet finalen Opportunity Score
Hoher Score = Praxis braucht dich dringend
"""
import sqlite3
import logging
logger = logging.getLogger(__name__)

def compute_opportunity_score(lead: dict) -> tuple[int, list]:
    """
    Opportunity Score 0-100:
    Hoher Score = viel Potential für dich
    - Kein/schlechtes Instagram
    - Wenig Google Reviews
    - Kein Tracking/Analytics
    - Premium Praxis (zahlt gut)
    - DE/CH Fokus
    """
    score = 0
    reasons = []

    # Social Media Gap (max 35)
    ig_followers = int(lead.get("instagram_followers") or 0)
    ig_handle = lead.get("instagram_handle") or ""
    if not ig_handle:
        score += 35
        reasons.append("❌ Kein Instagram")
    elif ig_followers < 500:
        score += 25
        reasons.append(f"📉 Instagram schwach ({ig_followers} Follower)")
    elif ig_followers < 2000:
        score += 10
        reasons.append(f"📊 Instagram ausbaufähig ({ig_followers} Follower)")

    # Google Reviews Gap (max 25)
    g_rating = float(lead.get("google_rating") or 0)
    g_reviews = int(lead.get("google_reviews") or 0)
    if g_reviews < 20:
        score += 25
        reasons.append(f"⭐ Wenig Reviews ({g_reviews})")
    elif g_reviews < 50:
        score += 15
        reasons.append(f"⭐ Reviews ausbaufähig ({g_reviews})")
    if g_rating and g_rating < 4.3:
        score += 10
        reasons.append(f"⚠️ Rating niedrig ({g_rating})")

    # Kein Marketing System (max 20)
    tracking = lead.get("tracking_tags") or ""
    if "google-ads" not in tracking.lower() and "adwords" not in tracking.lower():
        score += 10
        reasons.append("❌ Kein Google Ads")
    if "facebook" not in tracking.lower() and "meta" not in tracking.lower():
        score += 5
        reasons.append("❌ Kein Meta Ads")
    if not tracking or tracking == "[]":
        score += 5
        reasons.append("❌ Kein Tracking")

    # Premium Praxis = zahlt gut (max 20)
    positioning = lead.get("positioning") or ""
    if positioning == "premium":
        score += 15
        reasons.append("💎 Premium Positionierung")
    signals = lead.get("premium_service_signals") or ""
    if any(s in signals.lower() for s in ["all-on-4", "vollnarkose", "veneers", "implantate"]):
        score += 5
        reasons.append("✅ High-Value Services")

    # Land Bonus
    domain = lead.get("domain") or ""
    if domain.endswith(".ch"):
        score += 5
        reasons.append("🇨🇭 Schweiz (höhere Preise)")

    return min(score, 100), reasons

def run_opportunity_scoring():
    conn = sqlite3.connect("data/leads.db")
    try:
        conn.execute("ALTER TABLE companies ADD COLUMN opportunity_score INTEGER DEFAULT 0")
        conn.execute("ALTER TABLE companies ADD COLUMN opportunity_reasons TEXT DEFAULT ''")
    except Exception:
        pass
    conn.commit()

    leads = conn.execute("""
        SELECT id, domain, practice_name, city, positioning,
               instagram_handle, instagram_followers, google_rating,
               google_reviews, tracking_tags, premium_service_signals
        FROM companies WHERE status IN ('scored', 'enriched', 'profiled')
    """).fetchall()

    cols = ["id", "domain", "practice_name", "city", "positioning",
            "instagram_handle", "instagram_followers", "google_rating",
            "google_reviews", "tracking_tags", "premium_service_signals"]

    print(f"🎯 Opportunity Scoring für {len(leads)} Praxen...")
    results = []
    for row in leads:
        lead = dict(zip(cols, row))
        opp_score, reasons = compute_opportunity_score(lead)
        conn.execute(
            "UPDATE companies SET opportunity_score = ?, opportunity_reasons = ? WHERE id = ?",
            (opp_score, " | ".join(reasons), lead["id"])
        )
        results.append((opp_score, lead["domain"], reasons))

    conn.commit()
    conn.close()

    results.sort(reverse=True)
    print(f"\n🏆 Top 10 Opportunity Leads:")
    for score, domain, reasons in results[:10]:
        print(f"  {score}/100 – {domain}")
        print(f"         {reasons[0] if reasons else ''}")

    print(f"\n✅ Opportunity Scoring abgeschlossen")

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    run_opportunity_scoring()
