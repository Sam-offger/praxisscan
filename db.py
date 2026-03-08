"""
db.py – SQLite database layer using sqlite-utils.

Tables:
  companies     – one row per unique domain
  contacts      – contact persons linked to company
  runs          – pipeline run log
  raw_data      – raw extraction + profiling JSON (for debugging/reprocessing)
"""
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import sqlite_utils

import config

logger = logging.getLogger(__name__)

DB_PATH = config.DB_PATH


def get_db() -> sqlite_utils.Database:
    db = sqlite_utils.Database(DB_PATH)
    _ensure_schema(db)
    return db


def _ensure_schema(db: sqlite_utils.Database):
    if "companies" not in db.table_names():
        db["companies"].create({
            "id":                    int,
            "domain":                str,
            "practice_name":         str,
            "address":               str,
            "city":                  str,
            "country":               str,
            "phones":                str,   # JSON
            "emails":                str,   # JSON
            "social_links":          str,   # JSON
            "tracking_tags":         str,   # JSON
            "conversion_signals":    str,   # JSON
            "premium_service_signals": str, # JSON
            "hiring_signal":         int,   # bool
            "team_size_class":       str,
            "team_size_confidence":  str,
            # Scores
            "total_score":           int,
            "score_tier":            str,
            "subscores":             str,   # JSON
            "score_reasons":         str,   # JSON
            # AI Profile
            "positioning":           str,
            "positioning_reason":    str,
            "service_focus":         str,   # JSON
            "pain_points":           str,   # JSON
            "outreach_angle":        str,
            "summary":               str,
            "profiler":              str,
            # Affinity
            "affinity_score":        int,
            "affinity_signals":      str,   # JSON
            "affinity_note":         str,
            # Meta
            "pages_crawled":         int,
            "status":                str,   # discovered|enriched|profiled|scored|exported
            "created_at":            str,
            "updated_at":            str,
        }, pk="id", not_null={"domain"})
        db["companies"].create_index(["domain"], unique=True)

    if "contacts" not in db.table_names():
        db["contacts"].create({
            "id":          int,
            "company_id":  int,
            "name":        str,
            "role":        str,
            "email":       str,
            "email_status": str,
            "created_at":  str,
        }, pk="id", foreign_keys=[("company_id", "companies", "id")])

    if "runs" not in db.table_names():
        db["runs"].create({
            "id":          int,
            "run_type":    str,
            "started_at":  str,
            "finished_at": str,
            "leads_found": int,
            "leads_enriched": int,
            "leads_scored": int,
            "errors":      int,
            "notes":       str,
        }, pk="id")

    if "raw_data" not in db.table_names():
        db["raw_data"].create({
            "id":         int,
            "domain":     str,
            "extraction": str,  # JSON
            "profile":    str,  # JSON
            "scoring":    str,  # JSON
            "saved_at":   str,
        }, pk="id")


def upsert_company(db: sqlite_utils.Database, data: Dict[str, Any]) -> int:
    """Insert or update a company record. Returns company ID."""
    now = datetime.utcnow().isoformat()

    def _j(v):
        return json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v

    row = {
        "domain":                  data.get("domain", ""),
        "practice_name":           data.get("practice_name", ""),
        "address":                 data.get("address") or "",
        "city":                    data.get("city", ""),
        "country":                 data.get("country", ""),
        "phones":                  _j(data.get("phones", [])),
        "emails":                  _j(data.get("emails", [])),
        "social_links":            _j(data.get("social_links", {})),
        "tracking_tags":           _j(data.get("tracking_tags", [])),
        "conversion_signals":      _j(data.get("conversion_signals", [])),
        "premium_service_signals": _j(data.get("premium_service_signals", [])),
        "hiring_signal":           int(bool(data.get("hiring_signal"))),
        "team_size_class":         data.get("team_size_proxy", {}).get("size_class", ""),
        "team_size_confidence":    data.get("team_size_proxy", {}).get("confidence", ""),
        "total_score":             data.get("total_score", 0),
        "score_tier":              data.get("score_tier", ""),
        "subscores":               _j(data.get("subscores", {})),
        "score_reasons":           _j(data.get("score_reasons", {})),
        "positioning":             data.get("positioning", ""),
        "positioning_reason":      data.get("positioning_reason", ""),
        "service_focus":           _j(data.get("service_focus", [])),
        "pain_points":             _j(data.get("pain_points", [])),
        "outreach_angle":          data.get("outreach_angle", ""),
        "summary":                 data.get("summary", ""),
        "profiler":                data.get("profiler", ""),
        "affinity_score":          data.get("affinity_score", 0),
        "affinity_signals":        _j(data.get("affinity_signals", [])),
        "affinity_note":           data.get("affinity_note", ""),
        "pages_crawled":           len(data.get("pages_crawled", [])),
        "status":                  data.get("status", "discovered"),
        "updated_at":              now,
    }

    # Check if exists
    existing = list(db["companies"].rows_where("domain = ?", [row["domain"]]))
    if existing:
        db["companies"].update(existing[0]["id"], row)
        return existing[0]["id"]
    else:
        row["created_at"] = now
        return db["companies"].insert(row).last_pk


def upsert_contacts(db: sqlite_utils.Database, company_id: int, contacts: List[Dict]):
    now = datetime.utcnow().isoformat()
    for c in contacts:
        existing = list(db["contacts"].rows_where(
            "company_id = ? AND name = ?", [company_id, c.get("name", "")]
        ))
        if not existing:
            db["contacts"].insert({
                "company_id": company_id,
                "name":        c.get("name", ""),
                "role":        c.get("role", ""),
                "email":       c.get("email", ""),
                "email_status": c.get("status", ""),
                "created_at":  now,
            })


def save_raw(db: sqlite_utils.Database, domain: str,
             extraction: Dict, profile: Dict, scoring: Dict):
    now = datetime.utcnow().isoformat()
    existing = list(db["raw_data"].rows_where("domain = ?", [domain]))
    row = {
        "domain":     domain,
        "extraction": json.dumps(extraction, ensure_ascii=False),
        "profile":    json.dumps(profile, ensure_ascii=False),
        "scoring":    json.dumps(scoring, ensure_ascii=False),
        "saved_at":   now,
    }
    if existing:
        db["raw_data"].update(existing[0]["id"], row)
    else:
        db["raw_data"].insert(row)


def log_run(db: sqlite_utils.Database, run_type: str,
            started_at: str, finished_at: str,
            leads_found: int = 0, leads_enriched: int = 0,
            leads_scored: int = 0, errors: int = 0, notes: str = ""):
    db["runs"].insert({
        "run_type":       run_type,
        "started_at":     started_at,
        "finished_at":    finished_at,
        "leads_found":    leads_found,
        "leads_enriched": leads_enriched,
        "leads_scored":   leads_scored,
        "errors":         errors,
        "notes":          notes,
    })


def get_pending_discovery(db: sqlite_utils.Database) -> List[Dict]:
    return list(db["companies"].rows_where("status = 'discovered'"))


def get_pending_enrichment(db: sqlite_utils.Database) -> List[Dict]:
    return list(db["companies"].rows_where("status IN ('discovered', 'enriched')"))


def domain_exists(db: sqlite_utils.Database, domain: str) -> bool:
    return len(list(db["companies"].rows_where("domain = ?", [domain]))) > 0


def get_all_companies(db: sqlite_utils.Database) -> List[Dict]:
    return list(db["companies"].rows)
