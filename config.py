"""
config.py – Central configuration for Dental Lead System.
All values can be overridden via environment variables or a .env file.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
DB_PATH     = BASE_DIR / "data" / "leads.db"
EXPORTS_DIR = BASE_DIR / "exports"
LOGS_DIR    = BASE_DIR / "logs"

for _d in (DB_PATH.parent, EXPORTS_DIR, LOGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── Search / Discovery ────────────────────────────────────────────────────────
SEARCH_PROVIDER     = os.getenv("SEARCH_PROVIDER", "duckduckgo")   # duckduckgo | serper | serpapi
SERPER_API_KEY      = os.getenv("SERPER_API_KEY", "")
SERPAPI_API_KEY     = os.getenv("SERPAPI_API_KEY", "")
SEARCH_RESULTS_PER_QUERY = int(os.getenv("SEARCH_RESULTS_PER_QUERY", "10"))
DISCOVERY_QUERIES_DACH = [
    "Zahnarzt Implantate Veneers Premium Klinik",
    "Zahnklinik All-on-4 Vollnarkose",
    "Premium Zahnarztpraxis Smile Makeover",
    "Implantologie Spezialist Privatpraxis",
    "Zahnklinik Sedierung Invisalign Premium",
    "Zahnarzt Privatpatienten Veneer Spezialist",
    "Zahnklinik Österreich Implantate Veneers",
    "Premium Zahnarztpraxis Schweiz Implantologie",
]

# ── Crawler ───────────────────────────────────────────────────────────────────
MAX_PAGES_PER_DOMAIN  = int(os.getenv("MAX_PAGES_PER_DOMAIN", "10"))
CRAWL_TIMEOUT_S       = int(os.getenv("CRAWL_TIMEOUT_S", "15"))
CRAWL_DELAY_S         = float(os.getenv("CRAWL_DELAY_S", "2.0"))
CRAWL_MAX_RETRIES     = int(os.getenv("CRAWL_MAX_RETRIES", "3"))
RESPECT_ROBOTS_TXT    = os.getenv("RESPECT_ROBOTS_TXT", "true").lower() == "true"
USER_AGENT            = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (compatible; DentalLeadBot/1.0; +https://example.com/bot)"
)

PRIORITY_PATHS = [
    "/", "/kontakt", "/contact", "/impressum", "/imprint",
    "/team", "/leistungen", "/services", "/preise", "/prices",
    "/karriere", "/jobs", "/blog", "/uber-uns", "/about",
]

# ── AI Profiling ──────────────────────────────────────────────────────────────
AI_PROVIDER   = os.getenv("AI_PROVIDER", "ollama")   # ollama | openai | anthropic | rules
OLLAMA_HOST   = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL  = os.getenv("OLLAMA_MODEL", "llama3")
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL      = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL   = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

# ── Scoring ───────────────────────────────────────────────────────────────────
SCORE_THRESHOLD_TOP    = int(os.getenv("SCORE_THRESHOLD_TOP", "70"))
SCORE_THRESHOLD_REVIEW = int(os.getenv("SCORE_THRESHOLD_REVIEW", "40"))

# ── Affinity (optional – signals-only, not religion inference) ────────────────
AFFINITY_ENABLED = os.getenv("AFFINITY_ENABLED", "true").lower() == "true"

# ── Rate Limiting ─────────────────────────────────────────────────────────────
REQUESTS_PER_MINUTE = int(os.getenv("REQUESTS_PER_MINUTE", "20"))

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
