"""
pipeline.py – Orchestrates the full lead generation pipeline.

Steps:
  1. discover  → find URLs via search
  2. enrich    → crawl + extract structured data
  3. profile   → AI profiling
  4. score     → lead scoring
  5. export    → CSV exports
"""
import json
import logging
import time
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse

import config
from crawler import crawl_domain
from dedup import normalize_domain, is_duplicate, deduplicate_urls
from db import (
    get_db, upsert_company, upsert_contacts, save_raw,
    log_run, domain_exists, get_all_companies
)
from email_validate import validate_email_list
from extractor import extract_all
from ai_profiler import profile_lead
from scorer import compute_score
from providers.search_provider_factory import get_search_provider

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# DISCOVER
# ─────────────────────────────────────────────────────────────────────────────

def run_discover(queries=None, max_per_query=10):
    db = get_db()
    queries = queries or config.DISCOVERY_QUERIES_DACH
    found_urls = []

    # Multi-Source: alle verfügbaren Provider nutzen
    try:
        from providers.search_provider_factory import get_all_providers
        providers = get_all_providers()
    except Exception:
        from providers.search_provider_factory import get_search_provider
        providers = [(config.SEARCH_PROVIDER, get_search_provider())]

    for provider_name, provider in providers:
        logger.info(f"[DISCOVER] Provider: {provider_name}")
        for query in queries:
            logger.info(f"[DISCOVER] Searching: {query}")
            try:
                results = provider.search(query, num_results=max_per_query)
                for r in results:
                    found_urls.append(r.url)
                import time
                time.sleep(config.CRAWL_DELAY_S)
            except Exception as e:
                logger.warning(f"[DISCOVER] Search failed: {e}")

    found_urls = deduplicate_urls(found_urls)
    logger.info(f"[DISCOVER] {len(found_urls)} unique URLs from all sources")

    new_count = 0
    existing_companies = get_all_companies(db)

    for url in found_urls:
        domain = normalize_domain(url)
        if not domain or len(domain) < 4:
            continue
        if domain_exists(db, domain):
            continue
        is_dup, reason = is_duplicate(domain, "", "", existing_companies)
        if is_dup:
            continue
        if not _looks_like_dental(url, domain):
            continue
        upsert_company(db, {"domain": domain, "practice_name": "", "status": "discovered"})
        new_count += 1
        existing_companies.append({"domain": domain, "practice_name": "", "city": ""})
        logger.info(f"[DISCOVER] New lead: {domain}")

    logger.info(f"[DISCOVER] Done. {new_count} new leads added.")
    return new_count



def _looks_like_dental(url: str, domain: str) -> bool:
    """Rough filter to skip obviously non-dental URLs."""
    skip_domains = {
        "google", "facebook", "instagram", "twitter", "linkedin",
        "youtube", "wikipedia", "amazon", "yelp", "reddit",
        "doctolib", "jameda", "healthline", "webmd", "gelbeseiten",
        "meinestadt", "stadtbranchenbuch",
    }
    domain_lower = domain.lower()
    for skip in skip_domains:
        if skip in domain_lower:
            return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# ENRICH
# ─────────────────────────────────────────────────────────────────────────────

def run_enrich(limit: int = 50) -> int:
    """
    Crawl and extract data for discovered leads.
    Returns number of successfully enriched leads.
    """
    db = get_db()
    # Get leads pending enrichment
    pending = list(db["companies"].rows_where("status = 'discovered'"))[:limit]
    logger.info(f"[ENRICH] {len(pending)} leads to enrich")

    enriched = 0
    errors = 0

    for company in pending:
        domain = company["domain"]
        url = f"https://{domain}"
        logger.info(f"[ENRICH] Crawling: {url}")

        try:
            pages = crawl_domain(url)
            if not pages:
                logger.warning(f"[ENRICH] No pages fetched for {domain}")
                db["companies"].update(company["id"], {"status": "enrich_failed"})
                errors += 1
                continue

            extracted = extract_all(pages, domain)

            # Validate emails
            extracted["emails"] = validate_email_list(extracted.get("emails", []))

            # Store contacts separately
            contacts = extracted.get("contact_persons", [])

            # Update company with extracted data
            extracted["status"] = "enriched"
            upsert_company(db, {**company, **extracted})

            # Save contacts
            if contacts:
                company_id = list(db["companies"].rows_where("domain = ?", [domain]))[0]["id"]
                upsert_contacts(db, company_id, contacts)

            enriched += 1
            logger.info(f"[ENRICH] Done: {domain} ({len(pages)} pages)")

        except Exception as e:
            logger.error(f"[ENRICH] Failed {domain}: {e}", exc_info=True)
            db["companies"].update(company["id"], {"status": "enrich_failed"})
            errors += 1

    logger.info(f"[ENRICH] Enriched: {enriched}, Errors: {errors}")
    return enriched


# ─────────────────────────────────────────────────────────────────────────────
# PROFILE
# ─────────────────────────────────────────────────────────────────────────────

def run_profile(limit: int = 50) -> int:
    """
    AI-profile enriched leads.
    Returns number of profiled leads.
    """
    db = get_db()
    pending = list(db["companies"].rows_where("status = 'enriched'"))[:limit]
    logger.info(f"[PROFILE] {len(pending)} leads to profile")

    profiled = 0
    for company in pending:
        domain = company["domain"]
        logger.info(f"[PROFILE] Profiling: {domain}")
        try:
            # Reconstruct extracted dict from DB
            extracted = _company_to_extracted(company)
            profile = profile_lead(extracted)

            db["companies"].update(company["id"], {
                "positioning":        profile.get("positioning", ""),
                "positioning_reason": profile.get("positioning_reason", ""),
                "service_focus":      json.dumps(profile.get("service_focus", []), ensure_ascii=False),
                "pain_points":        json.dumps(profile.get("pain_points", []), ensure_ascii=False),
                "outreach_angle":     profile.get("outreach_angle", ""),
                "summary":            profile.get("summary", ""),
                "profiler":           profile.get("profiler", ""),
                "status":             "profiled",
                "updated_at":         datetime.utcnow().isoformat(),
            })

            # Save raw for debugging
            save_raw(db, domain, extracted, profile, {})
            profiled += 1

        except Exception as e:
            logger.error(f"[PROFILE] Failed {domain}: {e}", exc_info=True)

    logger.info(f"[PROFILE] Done: {profiled}")
    return profiled


# ─────────────────────────────────────────────────────────────────────────────
# SCORE
# ─────────────────────────────────────────────────────────────────────────────

def run_score(limit: int = 200) -> int:
    """
    Score profiled leads.
    Returns number of scored leads.
    """
    db = get_db()
    pending = list(db["companies"].rows_where("status = 'profiled'"))[:limit]
    logger.info(f"[SCORE] {len(pending)} leads to score")

    scored = 0
    for company in pending:
        domain = company["domain"]
        try:
            extracted = _company_to_extracted(company)
            profile = _company_to_profile(company)
            scoring = compute_score(extracted, profile)

            db["companies"].update(company["id"], {
                "total_score":  scoring["total_score"],
                "score_tier":   scoring["score_tier"],
                "subscores":    json.dumps(scoring["subscores"], ensure_ascii=False),
                "score_reasons": json.dumps(scoring["score_reasons"], ensure_ascii=False),
                "status":       "scored",
                "updated_at":   datetime.utcnow().isoformat(),
            })
            scored += 1

        except Exception as e:
            logger.error(f"[SCORE] Failed {domain}: {e}", exc_info=True)

    logger.info(f"[SCORE] Done: {scored}")
    return scored


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────────────────────────────────────────

def run_export() -> dict:
    """
    Export leads to CSV files.
    Returns dict with counts per file.
    """
    import csv

    db = get_db()
    all_companies = list(db["companies"].rows_where("status = 'scored'"))

    def _flatten(company: dict) -> dict:
        """Flatten JSON fields and return export-ready dict."""
        row = {k: v for k, v in company.items()}
        # Parse JSON arrays/dicts to readable strings
        for field in ["emails", "phones", "social_links", "tracking_tags",
                      "conversion_signals", "premium_service_signals",
                      "service_focus", "pain_points", "subscores", "score_reasons",
                      "affinity_signals"]:
            val = row.get(field, "")
            if isinstance(val, str) and val.startswith(("[", "{")):
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, list):
                        row[field] = "; ".join(
                            str(e.get("email", e) if isinstance(e, dict) else e)
                            for e in parsed
                        )
                    elif isinstance(parsed, dict):
                        row[field] = "; ".join(f"{k}={v}" for k, v in parsed.items())
                except Exception:
                    pass
        return row

    # All scored leads
    all_flat = [_flatten(c) for c in all_companies]
    all_path = config.EXPORTS_DIR / "leads_all.csv"
    _write_csv(all_flat, all_path)

    # Top leads
    top = [c for c in all_companies if (c.get("total_score") or 0) >= config.SCORE_THRESHOLD_TOP]
    top_flat = [_flatten(c) for c in top]
    top_path = config.EXPORTS_DIR / "leads_top.csv"
    _write_csv(top_flat, top_path)

    # Review queue: incomplete but mid-score
    review = [
        c for c in all_companies
        if config.SCORE_THRESHOLD_REVIEW <= (c.get("total_score") or 0) < config.SCORE_THRESHOLD_TOP
    ]
    review_flat = [_flatten(c) for c in review]
    review_path = config.EXPORTS_DIR / "review_queue.csv"
    _write_csv(review_flat, review_path)

    logger.info(f"[EXPORT] all={len(all_flat)}, top={len(top_flat)}, review={len(review_flat)}")
    return {"all": len(all_flat), "top": len(top_flat), "review": len(review_flat)}


def _write_csv(rows: list, path):
    if not rows:
        path.write_text("no_data\n")
        return
    import csv
    keys = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
    logger.info(f"Wrote {len(rows)} rows → {path}")


# ─────────────────────────────────────────────────────────────────────────────
# FULL RUN
# ─────────────────────────────────────────────────────────────────────────────

def run_full(queries=None):
    """Run the complete pipeline end-to-end."""
    started = datetime.utcnow().isoformat()
    db = get_db()

    logger.info("=" * 60)
    logger.info("FULL PIPELINE RUN STARTED")
    logger.info("=" * 60)

    found    = run_discover(queries=queries)
    enriched = run_enrich()
    profiled = run_profile()
    scored   = run_score()
    exports  = run_export()

    finished = datetime.utcnow().isoformat()
    log_run(db, "full_run", started, finished,
            leads_found=found, leads_enriched=enriched,
            leads_scored=scored,
            notes=str(exports))

    logger.info(f"DONE. Found={found} Enriched={enriched} Profiled={profiled} "
                f"Scored={scored} Exported={exports}")
    return {"found": found, "enriched": enriched, "profiled": profiled,
            "scored": scored, "exported": exports}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _parse_json_field(val, default):
    if isinstance(val, (list, dict)):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return default
    return default


def _company_to_extracted(company: dict) -> dict:
    return {
        "domain":                  company.get("domain", ""),
        "practice_name":           company.get("practice_name", ""),
        "city":                    company.get("city", ""),
        "country":                 company.get("country", ""),
        "address":                 company.get("address", ""),
        "emails":                  _parse_json_field(company.get("emails", "[]"), []),
        "phones":                  _parse_json_field(company.get("phones", "[]"), []),
        "social_links":            _parse_json_field(company.get("social_links", "{}"), {}),
        "tracking_tags":           _parse_json_field(company.get("tracking_tags", "[]"), []),
        "conversion_signals":      _parse_json_field(company.get("conversion_signals", "[]"), []),
        "premium_service_signals": _parse_json_field(company.get("premium_service_signals", "[]"), []),
        "hiring_signal":           bool(company.get("hiring_signal", 0)),
        "team_size_proxy": {
            "size_class":  company.get("team_size_class", ""),
            "confidence":  company.get("team_size_confidence", ""),
        },
        "affinity_score":  company.get("affinity_score", 0),
        "raw_text_snippet": "",  # Not stored, use empty for re-scoring
    }


def _company_to_profile(company: dict) -> dict:
    return {
        "positioning":        company.get("positioning", ""),
        "positioning_reason": company.get("positioning_reason", ""),
        "service_focus":      _parse_json_field(company.get("service_focus", "[]"), []),
        "pain_points":        _parse_json_field(company.get("pain_points", "[]"), []),
        "outreach_angle":     company.get("outreach_angle", ""),
        "summary":            company.get("summary", ""),
    }
