from typing import Any, Dict, Tuple
import config

def score_premium_fit(extracted: Dict, profile: Dict) -> Tuple[int, str]:
    score = 0
    reasons = []
    positioning = profile.get("positioning", "unclear")
    if positioning == "premium":
        score += 20
        reasons.append("AI classified as premium (+20)")
    elif positioning == "mid-range":
        score += 10
        reasons.append("AI classified as mid-range (+10)")
    signals = extracted.get("premium_service_signals", [])
    premium_high_value = {"all-on-4", "veneers", "smile makeover", "vollnarkose", "sedierung",
                          "implantologie", "implantology", "sofortimplantat", "ceramic crowns", "zirconia"}
    high_value_hits = len([s for s in signals if s.lower() in premium_high_value])
    kw_score = min(high_value_hits * 2, 10)
    score += kw_score
    if kw_score:
        reasons.append(f"Premium keywords ({high_value_hits} high-value): +{kw_score}")
    score = min(score, 30)
    return score, "; ".join(reasons) or "No premium signals detected"

def score_team_size(extracted: Dict, profile: Dict) -> Tuple[int, str]:
    proxy = extracted.get("team_size_proxy", {})
    size_class = proxy.get("size_class", "1-4")
    confidence = proxy.get("confidence", "low")
    docs = proxy.get("distinct_doctors_found", 0)
    if size_class == "10+":
        score = 18 if confidence == "medium" else 12
    elif size_class == "5-10":
        score = 10
    else:
        score = 3
    if extracted.get("hiring_signal"):
        score = min(score + 4, 20)
        reason = f"Size class: {size_class}, {docs} doctors found, hiring active -> {score}/20"
    else:
        reason = f"Size class: {size_class}, {docs} doctors found -> {score}/20"
    return min(score, 20), reason

def score_revenue_likelihood(extracted: Dict, profile: Dict) -> Tuple[int, str]:
    score = 0
    factors = []
    if profile.get("positioning") == "premium":
        score += 8
        factors.append("premium positioning (+8)")
    size = extracted.get("team_size_proxy", {}).get("size_class", "1-4")
    if size == "10+":
        score += 6
        factors.append("10+ team proxy (+6)")
    elif size == "5-10":
        score += 3
        factors.append("5-10 team proxy (+3)")
    high_ticket = {"all-on-4", "veneers", "smile makeover", "vollnarkose", "sofortimplantat", "full arch"}
    hits = len([s for s in extracted.get("premium_service_signals", []) if s in high_ticket])
    svc_score = min(hits * 2, 6)
    score += svc_score
    if svc_score:
        factors.append(f"high-ticket services ({hits}) (+{svc_score})")
    score = min(score, 20)
    return score, "; ".join(factors) or "Insufficient data for revenue proxy"

def score_growth_gap(extracted: Dict, profile: Dict) -> Tuple[int, str]:
    score = 0
    gaps = []
    tracking = extracted.get("tracking_tags", [])
    if not tracking:
        score += 5
        gaps.append("no tracking/analytics (+5)")
    elif len(tracking) <= 1:
        score += 2
        gaps.append("minimal tracking (+2)")
    conversion = extracted.get("conversion_signals", [])
    if not conversion:
        score += 4
        gaps.append("no online booking/conversion (+4)")
    elif len(conversion) <= 1:
        score += 2
        gaps.append("weak conversion setup (+2)")
    socials = extracted.get("social_links", {})
    if not socials:
        score += 4
        gaps.append("no social presence (+4)")
    elif len(socials) <= 1:
        score += 2
        gaps.append("limited social presence (+2)")
    pain_points = profile.get("pain_points", [])
    if "marketing_gap" in pain_points and score < 15:
        score += 2
        gaps.append("AI confirmed marketing gap (+2)")
    score = min(score, 15)
    return score, "; ".join(gaps) or "Digital infrastructure appears adequate"

def score_buying_signals(extracted: Dict, profile: Dict) -> Tuple[int, str]:
    score = 0
    signals = []
    if extracted.get("hiring_signal"):
        score += 4
        signals.append("actively hiring (+4)")
    tracking = extracted.get("tracking_tags", [])
    if "google_tag_manager" in tracking or "google_analytics" in tracking:
        score += 2
        signals.append("has analytics (+2)")
    if "meta_pixel" in tracking:
        score += 2
        signals.append("runs paid ads (+2)")
    conversion = extracted.get("conversion_signals", [])
    if "booking_button" in conversion or "doctolib" in conversion:
        score += 2
        signals.append("online booking present (+2)")
    score = min(score, 10)
    return score, "; ".join(signals) or "No specific buying signals"

def score_data_completeness(extracted: Dict) -> Tuple[int, str]:
    score = 0
    present = []
    missing = []
    if extracted.get("emails"):
        score += 2
        present.append("email")
    else:
        missing.append("email")
    if extracted.get("phones"):
        score += 1
        present.append("phone")
    else:
        missing.append("phone")
    if extracted.get("address") or extracted.get("city"):
        score += 1
        present.append("address/city")
    else:
        missing.append("address/city")
    if extracted.get("contact_persons"):
        score += 1
        present.append("contact person")
    else:
        missing.append("contact person")
    reason = f"Present: {', '.join(present) or 'none'}"
    if missing:
        reason += f" | Missing: {', '.join(missing)}"
    return score, reason

def compute_score(extracted: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
    p_score, p_reason = score_premium_fit(extracted, profile)
    t_score, t_reason = score_team_size(extracted, profile)
    r_score, r_reason = score_revenue_likelihood(extracted, profile)
    g_score, g_reason = score_growth_gap(extracted, profile)
    b_score, b_reason = score_buying_signals(extracted, profile)
    d_score, d_reason = score_data_completeness(extracted)
    base = p_score + t_score + r_score + g_score + b_score + d_score
    affinity_raw = extracted.get("affinity_score", 0)
    affinity_bonus = min(round(affinity_raw / 2), 5)
    total = min(base + affinity_bonus, 100)
    return {
        "total_score": total,
        "subscores": {
            "premium_fit":       p_score,
            "team_size":         t_score,
            "revenue_proxy":     r_score,
            "growth_gap":        g_score,
            "buying_signals":    b_score,
            "data_completeness": d_score,
            "affinity_bonus":    affinity_bonus,
        },
        "score_reasons": {
            "premium_fit":       p_reason,
            "team_size":         t_reason,
            "revenue_proxy":     r_reason,
            "growth_gap":        g_reason,
            "buying_signals":    b_reason,
            "data_completeness": d_reason,
        },
        "score_tier": _tier(total),
    }

def _tier(score: int) -> str:
    if score >= config.SCORE_THRESHOLD_TOP:
        return "top"
    elif score >= config.SCORE_THRESHOLD_REVIEW:
        return "review"
    else:
        return "low"
