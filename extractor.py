"""
extractor.py – Extracts structured data from crawled HTML pages.

Extracts: practice name, address, emails, phone, social links,
premium service signals, tracking tags, conversion signals,
contact persons, and affinity signals.
"""
import re
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ── Regex Patterns ─────────────────────────────────────────────────────────────

EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)
PHONE_RE = re.compile(
    r"(?:\+?\d[\d\s\-().]{7,})"
)
SOCIAL_PATTERNS = {
    "instagram": re.compile(r"instagram\.com/([^/\s\"'>]+)", re.I),
    "facebook":  re.compile(r"facebook\.com/([^/\s\"'>]+)", re.I),
    "linkedin":  re.compile(r"linkedin\.com/(?:company|in)/([^/\s\"'>]+)", re.I),
    "youtube":   re.compile(r"youtube\.com/(?:@|channel|user)/([^/\s\"'>]+)", re.I),
    "tiktok":    re.compile(r"tiktok\.com/@([^/\s\"'>]+)", re.I),
}
TRACKING_PATTERNS = {
    "google_tag_manager": re.compile(r"GTM-[A-Z0-9]+", re.I),
    "google_analytics":   re.compile(r"UA-\d+-\d+|G-[A-Z0-9]+", re.I),
    "meta_pixel":         re.compile(r"fbq\s*\(|facebook\.com/tr", re.I),
    "hotjar":             re.compile(r"hotjar\.com|hjid", re.I),
    "hubspot":            re.compile(r"hubspot\.com|hs-scripts", re.I),
}
CONVERSION_SIGNALS = {
    "doctolib":        re.compile(r"doctolib\.(de|fr|at|com)", re.I),
    "jameda":          re.compile(r"jameda\.de", re.I),
    "booking_button":  re.compile(r"termin\s*buchen|jetzt\s*buchen|appointment|online\s*booking", re.I),
    "contact_form":    re.compile(r"<form[^>]*>", re.I),
    "phone_cta":       re.compile(r"jetzt\s*anrufen|call\s*now", re.I),
}

PREMIUM_KEYWORDS = [
    "veneers", "veneer", "implantate", "implants", "all-on-4", "all on 4",
    "smile makeover", "smile design", "invisalign", "aligner", "vollnarkose",
    "sedierung", "sedation", "implantologie", "implantology",
    "zahnästhetik", "ästhetische zahnmedizin", "cosmetic dentistry",
    "keramikkronen", "ceramic crowns", "digitalzahnmedizin",
    "premium", "privatpraxis", "private practice", "luxus", "exklusiv",
    "zirconia", "zirkon", "sofortimplantat", "immediate implant",
    "full arch", "guided surgery", "3d planung",
]

TEAM_KEYWORDS = [
    r"dr\.\s*med\.\s*dent", r"dr\.", r"zahnarzt", r"zahnärztin",
    r"kieferchirurg", r"implantologe", r"spezialist",
    r"unser\s+team", r"our\s+team", r"behandler",
]

HIRING_KEYWORDS = [
    r"stellenangebote?", r"jobs?", r"karriere", r"wir\s+suchen",
    r"we'?re?\s+hiring", r"open\s+positions?", r"mitarbeiter\s+gesucht",
    r"bewerbung", r"vollzeit", r"teilzeit", r"zahnarzt\s+gesucht",
]

AFFINITY_KEYWORDS = {
    "arabic_language":   re.compile(r"[\u0600-\u06FF]{3,}|arabisch|arabic|عربي|مرحبا", re.I),
    "turkish_language":  re.compile(r"türkisch|turkish|türkçe", re.I),
    "farsi_language":    re.compile(r"farsi|persisch|فارسی", re.I),
    "eid_ramadan":       re.compile(r"\beid\b|ramadan|عيد|رمضان", re.I),
    "halal_friendly":    re.compile(r"halal|حلال", re.I),
    "community_outreach": re.compile(r"community|gemeinde|interkulturell|multicultural", re.I),
    "multilingual":      re.compile(r"mehrsprachig|multilingual|wir\s+sprechen\s+(arabisch|türkisch|farsi)", re.I),
}

ROLE_KEYWORDS = re.compile(
    r"(inhaber|geschäftsführer|ärztliche\s+leitung|praxismanager|ceo|founder|owner|director)",
    re.I,
)


def _all_text(pages: Dict[str, str]) -> str:
    texts = []
    for html in pages.values():
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        texts.append(soup.get_text(separator=" ", strip=True))
    return " ".join(texts)


def _all_raw(pages: Dict[str, str]) -> str:
    return " ".join(pages.values())


def extract_emails(text: str, domain: str) -> List[Dict[str, str]]:
    found = list(set(EMAIL_RE.findall(text)))
    results = []
    for email in found:
        email = email.lower()
        # Filter junk
        if any(skip in email for skip in ["example.com", "sentry.io", "schema.org", "w3.org"]):
            continue
        email_domain = email.split("@")[1]
        results.append({
            "email": email,
            "type": "domain_email" if email_domain == domain.lstrip("www.") else "provider_email",
        })
    return results[:10]  # cap at 10


def extract_phones(text: str) -> List[str]:
    raw = PHONE_RE.findall(text)
    cleaned = []
    for p in raw:
        p = re.sub(r"\s+", " ", p).strip()
        # Must have at least 8 digits
        digits = re.sub(r"\D", "", p)
        if len(digits) >= 8:
            cleaned.append(p)
    return list(dict.fromkeys(cleaned))[:5]


def extract_social_links(raw_html: str) -> Dict[str, str]:
    result = {}
    for platform, pattern in SOCIAL_PATTERNS.items():
        m = pattern.search(raw_html)
        if m:
            result[platform] = m.group(0) if platform not in result else result[platform]
    return result


def extract_tracking(raw_html: str) -> List[str]:
    found = []
    for name, pattern in TRACKING_PATTERNS.items():
        if pattern.search(raw_html):
            found.append(name)
    return found


def extract_conversion_signals(text: str, raw_html: str) -> List[str]:
    found = []
    for name, pattern in CONVERSION_SIGNALS.items():
        target = raw_html if name in ("contact_form",) else text
        if pattern.search(target):
            found.append(name)
    return found


def extract_premium_signals(text: str) -> List[str]:
    text_lower = text.lower()
    found = [kw for kw in PREMIUM_KEYWORDS if kw.lower() in text_lower]
    return list(set(found))


def extract_hiring_signals(text: str) -> bool:
    text_lower = text.lower()
    return any(re.search(kw, text_lower) for kw in HIRING_KEYWORDS)


def extract_team_size_proxy(text: str) -> Dict[str, Any]:
    """
    Estimate team size from text mentions of doctors/team members.
    Returns a dict with count proxy and confidence.
    """
    text_lower = text.lower()
    # Count distinct doctor mentions
    doctor_names = re.findall(r"dr\.?\s+[A-ZÄÖÜ][a-zäöü]+\s+[A-ZÄÖÜ][a-zäöü]+", text)
    distinct_doctors = len(set(doctor_names))

    hiring_active = extract_hiring_signals(text)

    # Rough proxies
    if distinct_doctors >= 5 or (distinct_doctors >= 3 and hiring_active):
        size_class = "10+"
        confidence = "medium"
    elif distinct_doctors >= 2:
        size_class = "5-10"
        confidence = "low"
    else:
        size_class = "1-4"
        confidence = "low"

    return {
        "size_class": size_class,
        "distinct_doctors_found": distinct_doctors,
        "confidence": confidence,
    }


def extract_practice_name(pages: Dict[str, str], domain: str) -> str:
    """Try to extract practice name from <title> or <h1>."""
    for url, html in pages.items():
        if urlparse(url).path in ("", "/", "/index.html"):
            soup = BeautifulSoup(html, "lxml")
            title = soup.find("title")
            if title:
                name = title.get_text(strip=True).split("|")[0].split("–")[0].split("-")[0].strip()
                if 3 < len(name) < 80:
                    return name
            h1 = soup.find("h1")
            if h1:
                return h1.get_text(strip=True)[:80]
    # Fallback: use domain
    return domain.replace("www.", "").split(".")[0].title()


def extract_address(text: str) -> Optional[str]:
    """
    Simple heuristic: find lines that look like German/AT/CH addresses.
    Pattern: Straße/Weg/Platz + number, ZIP + City
    """
    pattern = re.compile(
        r"([A-ZÄÖÜ][a-zäöü\-]+(?:straße|strasse|weg|platz|gasse|allee|ring|damm|chaussee)\s+\d+[\w/]*"
        r"[,\s]+\d{4,5}\s+[A-ZÄÖÜ][a-zäöü]+)",
        re.I,
    )
    m = pattern.search(text)
    if m:
        return m.group(0).strip()
    return None


def extract_city_country(text: str, domain: str) -> Dict[str, str]:
    """Guess city and country from TLD and text."""
    tld = domain.rsplit(".", 1)[-1].lower() if "." in domain else ""
    country_map = {"de": "DE", "at": "AT", "ch": "CH", "co.uk": "UK", "com": ""}
    country = country_map.get(tld, "")

    # Try to find city from address pattern
    city = ""
    m = re.search(r"\d{5}\s+([A-ZÄÖÜ][a-zäöü\-]+)", text)
    if not m:
        m = re.search(r"\d{4}\s+([A-ZÄÖÜ][a-zäöü\-]+)", text)  # AT/CH 4-digit
    if m:
        city = m.group(1)

    return {"city": city, "country": country}


def extract_contact_persons(text: str) -> List[Dict[str, str]]:
    """
    Extract contact persons (name + role) – only public business context.
    Only stores name + role, NO private data.
    """
    persons = []
    # Pattern: Dr. Firstname Lastname + possible role nearby
    pattern = re.compile(
        r"((?:Dr\.?\s+(?:med\.?\s+dent\.?\s+)?|Prof\.?\s+)?[A-ZÄÖÜ][a-zäöü]+\s+[A-ZÄÖÜ][a-zäöü]+)"
        r"(?:[^.]{0,100}?)(inhaber|geschäftsführer|ärztliche\s+leitung|praxisleitung|praxismanager|ceo|owner|founder|director)?",
        re.I,
    )
    seen = set()
    for m in pattern.finditer(text):
        name = m.group(1).strip()
        role = m.group(2).strip() if m.group(2) else ""
        if name not in seen and len(name.split()) == 2:
            seen.add(name)
            persons.append({"name": name, "role": role})
            if len(persons) >= 5:
                break
    return persons


def extract_affinity_signals(text: str) -> Dict[str, Any]:
    """
    COMPLIANCE NOTE: This is purely signals-based on publicly visible business content.
    It does NOT infer religion. It detects language offerings and community keywords.
    Result is labelled 'signals-based affinity, not a statement of religion'.
    """
    if not __import__("config").AFFINITY_ENABLED:
        return {"affinity_score": 0, "affinity_signals": [], "affinity_note": "disabled"}

    signals = []
    for name, pattern in AFFINITY_KEYWORDS.items():
        if pattern.search(text):
            signals.append(name)

    score = min(len(signals) * 2, 10)
    return {
        "affinity_score": score,
        "affinity_signals": signals,
        "affinity_note": "Signals-based affinity (publicly visible business content only). Not a statement of religion or ethnicity.",
    }


def extract_all(pages: Dict[str, str], domain: str) -> Dict[str, Any]:
    """
    Master extraction function. Takes crawled pages and returns structured data.
    """
    text = _all_text(pages)
    raw_html = _all_raw(pages)

    emails = extract_emails(text, domain)
    phones = extract_phones(text)
    socials = extract_social_links(raw_html)
    tracking = extract_tracking(raw_html)
    conversion = extract_conversion_signals(text, raw_html)
    premium = extract_premium_signals(text)
    hiring = extract_hiring_signals(text)
    team_proxy = extract_team_size_proxy(text)
    name = extract_practice_name(pages, domain)
    address = extract_address(text)
    loc = extract_city_country(text, domain)
    persons = extract_contact_persons(text)
    affinity = extract_affinity_signals(text)

    return {
        "practice_name": name,
        "domain": domain,
        "address": address,
        "city": loc["city"],
        "country": loc["country"],
        "emails": emails,
        "phones": phones,
        "social_links": socials,
        "tracking_tags": tracking,
        "conversion_signals": conversion,
        "premium_service_signals": premium,
        "hiring_signal": hiring,
        "team_size_proxy": team_proxy,
        "contact_persons": persons,
        "pages_crawled": list(pages.keys()),
        **affinity,
        "raw_text_snippet": text[:2000],  # for AI profiling
    }
