# 🦷 Dental Lead System – Vollständige Dokumentation

---

## A) ARCHITEKTURÜBERSICHT

```
                    ┌─────────────────────────────────────────────────────┐
                    │                  CLI (cli.py)                        │
                    │   discover | enrich | profile | score | export       │
                    └───────────────────────┬─────────────────────────────┘
                                            │
                    ┌───────────────────────▼─────────────────────────────┐
                    │              Pipeline (pipeline.py)                  │
                    └──┬────────┬────────┬──────────┬─────────────────────┘
                       │        │        │          │
          ┌────────────▼─┐  ┌───▼────┐ ┌▼────────┐ ┌▼───────┐
          │   Discovery   │  │Crawler │ │AI Prof. │ │Scorer  │
          │ (SERP/DDG)    │  │       │ │(Ollama/ │ │(0-100) │
          │               │  │       │ │OpenAI/  │ │        │
          └──────┬────────┘  └───┬───┘ │rules)   │ └────┬───┘
                 │               │     └────┬────┘      │
                 │          ┌────▼────┐     │           │
                 │          │Extract. │     │           │
                 │          │(BS4+Re) │     │           │
                 │          └────┬────┘     │           │
                 │               │          │           │
                 └───────────────▼──────────▼───────────▼──────────┐
                                 │        Database (db.py)          │
                                 │          SQLite                  │
                                 │   companies | contacts | runs    │
                                 └────────────────┬─────────────────┘
                                                  │
                                        ┌─────────▼──────────┐
                                        │     CSV Export      │
                                        │  leads_all.csv      │
                                        │  leads_top.csv      │
                                        │  review_queue.csv   │
                                        └─────────────────────┘
```

**Datenfluss:**
1. `discover`: Suche via DuckDuckGo/Serper → URLs → Dedup → DB (status=discovered)
2. `enrich`: Crawl Domain (max 10 Seiten) → Extract (Email/Phone/Signals) → Email-Validierung → DB (status=enriched)
3. `profile`: AI analysiert Text → JSON-Profil (Positionierung/Pain Points/Angle) → DB (status=profiled)
4. `score`: 6 Komponenten → Total 0–100 → Tier (top/review/low) → DB (status=scored)
5. `export`: CSV exports für alle/top/review

---

## B) REPO-LAYOUT

```
dental_leads/
├── .env.example              ← Konfigurationsvorlage
├── .env                      ← DEINE Konfiguration (nicht committen!)
├── requirements.txt          ← Python Pakete
├── config.py                 ← Zentrale Konfiguration
├── cli.py                    ← Kommandozeile (Einstiegspunkt)
├── pipeline.py               ← Haupt-Orchestrierung
├── crawler.py                ← Website-Crawler
├── extractor.py              ← Daten-Extraktion aus HTML
├── ai_profiler.py            ← AI Profiling (Ollama/OpenAI/Rules)
├── scorer.py                 ← Lead Scoring Engine
├── dedup.py                  ← Deduplizierung
├── email_validate.py         ← Email Syntax + MX Check
├── db.py                     ← SQLite Datenbankschicht
├── README.md                 ← Kurzanleitung
├── VOLLSTÄNDIGE_DOKUMENTATION.md  ← Diese Datei
├── providers/
│   ├── __init__.py
│   ├── search_provider_base.py    ← Abstract Base Class
│   ├── search_provider_duckduckgo.py  ← Kostenlos (default)
│   ├── search_provider_serper.py      ← Optional (paid)
│   └── search_provider_factory.py    ← Provider-Selektion
├── tests/
│   ├── __init__.py
│   ├── test_extractor.py     ← Tests für Extraktion
│   ├── test_scorer.py        ← Tests für Scoring
│   └── test_dedup.py         ← Tests für Dedup
├── data/
│   └── leads.db              ← SQLite Datenbank (auto-erstellt)
├── exports/
│   ├── leads_all.csv         ← Alle gescorten Leads
│   ├── leads_top.csv         ← Leads Score >= 70
│   └── review_queue.csv      ← Leads Score 40–69
└── logs/
    └── dental_leads.log      ← Logdatei
```

---

## C) INSTALLATION & SETUP

### Voraussetzungen
- Python 3.10 oder höher
- pip (kommt mit Python)
- Optional: Ollama (für lokale AI, kostenlos)

### Mac (Terminal)

```bash
# 1. Python prüfen
python3 --version  # muss 3.10+ sein

# 2. Projekt-Ordner erstellen
mkdir ~/dental_leads && cd ~/dental_leads

# 3. Alle Dateien hier einfügen (aus diesem Dokument)

# 4. Virtuelle Umgebung erstellen (empfohlen)
python3 -m venv venv
source venv/bin/activate

# 5. Pakete installieren
pip install -r requirements.txt

# 6. Konfiguration kopieren
cp .env.example .env

# 7. Ollama installieren (optional, für AI-Profiling)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3

# 8. Test-Run
python cli.py stats

# 9. Ersten vollständigen Run starten
python cli.py full-run
```

### Windows (PowerShell oder CMD)

```powershell
# 1. Python von python.org herunterladen (3.11 empfohlen)
# Beim Install: "Add Python to PATH" ankreuzen!

# 2. PowerShell als Administrator öffnen

# 3. Projekt-Ordner
mkdir C:\dental_leads
cd C:\dental_leads

# 4. Alle Dateien hier einfügen

# 5. Virtuelle Umgebung
python -m venv venv
.\venv\Scripts\Activate.ps1
# Falls Fehler: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 6. Pakete installieren
pip install -r requirements.txt

# 7. Konfiguration
copy .env.example .env

# 8. Ollama für Windows:
# https://ollama.com/download → Windows Installer
# Nach Installation in neuem Terminal:
ollama pull llama3

# 9. Starten
python cli.py full-run
```

### AI Provider ohne Ollama (falls kein Ollama möglich)

Im `.env` setzen:
```
AI_PROVIDER=rules
```
Das regelbasierte System funktioniert ohne jede Installation. Weniger intelligent, aber zuverlässig.

---

## D) ALLE CODE-DATEIEN

Alle Dateien sind im Repository enthalten. Inhalt dieser Dokumentation gibt Überblick.

### Wichtige Defaults (config.py)

| Variable | Default | Bedeutung |
|----------|---------|-----------|
| SEARCH_PROVIDER | duckduckgo | Suchanbieter (kostenlos) |
| AI_PROVIDER | ollama | LLM-Provider |
| MAX_PAGES_PER_DOMAIN | 10 | Max Seiten pro Domain |
| CRAWL_DELAY_S | 2.0 | Sekunden zwischen Anfragen |
| SCORE_THRESHOLD_TOP | 70 | Ab wann "Top Lead" |
| AFFINITY_ENABLED | true | Affinity-Signale aktiv |

---

## E) TESTPLAN

### 5 Beispiel-Discovery-Queries für DACH

1. **Breite Premium-Suche:**
   ```
   Zahnarzt Implantate Veneers Premium Klinik
   ```
   Erwartetes Ergebnis: Praxen mit mehreren Premium-Services, oft Großstädte.

2. **Nischen-Spezialist:**
   ```
   Zahnklinik All-on-4 Vollnarkose Sedierung
   ```
   Erwartetes Ergebnis: Spezialisierte Kliniken mit chirurgischer Kompetenz.

3. **Österreich/Schweiz-Fokus:**
   ```
   Premium Zahnarztpraxis Wien Implantologie
   Zahnklinik Zürich Veneers Smile Design
   ```
   Erwartetes Ergebnis: DACH-Coverage außerhalb Deutschlands.

4. **Wachstums-Signal:**
   ```
   Zahnarzt Privatpraxis Stellenangebote Implantologe
   ```
   Erwartetes Ergebnis: Wachsende Praxen mit Hiring-Signal.

5. **Cosmetic Focus:**
   ```
   Cosmetic Dentistry Smile Makeover Deutschland
   ```
   Erwartetes Ergebnis: Ästhetisch fokussierte Praxen, oft mit gutem Branding.

### Tests ausführen

```bash
cd tests
python -m pytest . -v --tb=short
```

Erwarteter Output:
```
test_extractor.py::TestEmailExtraction::test_finds_domain_email PASSED
test_extractor.py::TestPremiumSignals::test_detects_premium_keywords PASSED
test_scorer.py::TestScorerTotals::test_premium_lead_scores_high PASSED
test_dedup.py::TestIsDuplicate::test_exact_domain_match PASSED
... (alle grün)
```

---

## F) DEBUGGING-GUIDE

### Problem 1: DuckDuckGo liefert keine Ergebnisse

**Symptom:** `[DISCOVER] 0 unique URLs from search`

**Ursachen & Fixes:**
```bash
# A) DuckDuckGo hat IP temporär gedrosselt → warten
# B) User-Agent wird geblockt → in .env anpassen:
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0

# C) Serper als Alternative:
# → Kostenloser Account auf serper.dev, 2500 Gratis-Queries/Monat
# In .env:
SEARCH_PROVIDER=serper
SERPER_API_KEY=dein_key_hier
```

### Problem 2: Crawl schlägt fehl für alle Domains

**Symptom:** `[ENRICH] Errors: X, Enriched: 0`

**Fix:**
```bash
# Timeout erhöhen in .env:
CRAWL_TIMEOUT_S=30
CRAWL_DELAY_S=3.0

# Robots.txt temporär deaktivieren (nur für Debugging!):
RESPECT_ROBOTS_TXT=false

# Einzelne Domain testen:
python3 -c "
from crawler import crawl_domain
pages = crawl_domain('https://zahnarzt-beispiel.de')
print(len(pages), 'pages fetched')
"
```

### Problem 3: Ollama antwortet nicht

**Symptom:** `Ollama profiling failed: ConnectError`

**Fix:**
```bash
# Prüfen ob Ollama läuft:
curl http://localhost:11434/api/tags

# Neu starten:
ollama serve  # in separatem Terminal

# Auf rules-fallback wechseln:
# In .env: AI_PROVIDER=rules
```

### Problem 4: JSON Parse Error bei AI-Antwort

**Symptom:** `JSON parse failed`

**Fix:**
```
# Anderes Modell probieren (besseres Instruction-Following):
# In .env:
OLLAMA_MODEL=mistral
# oder:
OLLAMA_MODEL=llama3.1

# OpenAI als zuverlässigere Alternative (gpt-4o-mini ~$0.01/Lead):
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

### Problem 5: Keine Emails gefunden

**Symptom:** `emails: []` in allen Leads

**Debug:**
```python
# Testen mit einer konkreten Domain:
python3 -c "
from crawler import crawl_domain
from extractor import extract_all
pages = crawl_domain('https://zahnarzt-beispiel.de')
data = extract_all(pages, 'zahnarzt-beispiel.de')
print('Emails:', data['emails'])
print('Text snippet:', data['raw_text_snippet'][:500])
"
```
Manche Praxen obfuskieren Emails (JavaScript-Rendering, Bild-Email). 
→ Dann manuell nachrecherchieren und direkt in DB eintragen.

### Problem 6: ImportError / ModuleNotFoundError

**Symptom:** `ModuleNotFoundError: No module named 'xxx'`

**Fix:**
```bash
# Sicherstellen dass venv aktiv ist:
source venv/bin/activate  # Mac/Linux
.\venv\Scripts\Activate.ps1  # Windows

# Pakete neu installieren:
pip install -r requirements.txt --force-reinstall
```

### Problem 7: Scoring ergibt 0 für alle Leads

**Symptom:** Alle total_score = 0

**Ursache:** Status-Pipeline unterbrochen (z.B. alle Leads auf 'enriched' aber nicht profiled)

**Fix:**
```bash
python3 -c "
from db import get_db
db = get_db()
# Alle enriched direkt auf profiled setzen (mit Dummy-Profil):
for c in db['companies'].rows_where('status = chr(39) || enriched || chr(39)'):
    db['companies'].update(c['id'], {'status': 'profiled', 'positioning': 'unclear'})
"
python cli.py score
```

---

## G) ROADMAP v2

### 🗺️ Version 2.0 – 3-6 Monate

**Google Maps Integration (optional plugin, standardmäßig AUS)**
```python
# Geplantes Modul: providers/maps_provider.py
# Nutzt Google Maps API (kostenpflichtig) oder Apple Maps Scraping
# Extraktion: Bewertungsanzahl, Rating, Öffnungszeiten, Fotos-Count
# Compliance: Nur öffentliche Business-Listings, keine personenbezogenen Daten
```

**Review & Sentiment Analysis**
```python
# Geplantes Modul: enrichment/reviews.py
# Quellen: Jameda, Google Reviews (API), ProvenExpert
# Sentiment: positiv/negativ/neutral pro Kategorie (Service/Preis/Wartezeit)
# Use case: Praxen mit gutem Produkt aber schwacher Online-Reputation = idealer Lead
```

**Social Media Activity Scoring**
```python
# Geplantes Modul: enrichment/social_activity.py
# Instagram: Posting-Frequenz, Follower-Wachstum (public data only)
# LinkedIn: Company Page Activity
# Score: aktiv/inaktiv/nicht-vorhanden → Input für Growth-Gap Score
```

**CRM Sync**
```python
# Geplantes Modul: integrations/crm_sync.py
# HubSpot: hubspot_client.crm.contacts.create()
# Notion: Notion API
# Airtable: Airtable API
# Config: CRM_PROVIDER=hubspot / notion / airtable
```

**Erweiterte Regionen**
```
# Neue Query-Sets in config.py:
DISCOVERY_QUERIES_UK = ["premium dentist London", "dental implants clinic UK", ...]
DISCOVERY_QUERIES_US = ["cosmetic dentist NYC premium", "all-on-4 specialist USA", ...]
DISCOVERY_QUERIES_UAE = ["dental clinic Dubai free zone premium", ...]
```

**Website Technology Detection**
```python
# Wappalyzer-Integration: CMS, Booking-System, E-Commerce
# Use case: Wix/Squarespace = einfach zu upgraden
# WordPress ohne Plugin = Conversion-Gap
```

**Outreach Tracking**
```python
# Neue Tabelle: outreach_log
# Felder: company_id, contacted_at, channel, response, status
# CLI: python cli.py mark-contacted --domain zahnarzt.de --channel email
```

### Version 3.0 – 12 Monate

- Automated email sequence generation (per Lead-Profil)
- A/B Testing für Outreach-Angles
- Revenue tracking (Conversion from Lead to Client)
- Multi-user support mit Rollen
- Web UI (FastAPI + React)

---

## COMPLIANCE-HINWEISE

1. **Personenbezogene Daten**: Das System speichert ausschließlich öffentliche Business-Kontaktdaten (Impressum, Website, Business-Email). Keine Privatpersonen-Daten.

2. **Affinity-Tagging**: Ausschließlich auf Basis öffentlich sichtbarer Business-Signale (angebotene Sprachen, publizierte Inhalte). Kein Inferieren von Religion oder Ethnizität. Alle Outputs mit Compliance-Label versehen.

3. **Robots.txt**: Standard-Einstellung `RESPECT_ROBOTS_TXT=true` respektiert die Crawler-Richtlinien der Websites.

4. **Rate Limiting**: 2 Sekunden Pause zwischen Requests, max 20 Requests/Minute. Kein aggressives Scraping.

5. **DSGVO**: Da nur Business-Daten gespeichert werden (keine natürlichen Personen als Zielgruppe), ist das System grundsätzlich DSGVO-konform. Im Zweifel Rechtsberatung einholen.

6. **ToS**: DuckDuckGo-Scraping ist eine Grauzone. Für kommerzielle Nutzung empfiehlt sich ein bezahlter Search API Provider (Serper, SerpAPI).
