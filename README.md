# PraxisScan 🦷

**Automatisiertes B2B Lead Intelligence System für Zahnarztpraxen im DACH-Raum**

Entwickelt im Rahmen von [Arkan Creative](https://github.com/Sam-offger) zur vollautomatischen Kundenakquise.

---

## Was ist PraxisScan?

PraxisScan ist eine vollautomatische Datenpipeline, die Premium-Zahnarztpraxen im DACH-Raum (Deutschland, Österreich, Schweiz) identifiziert, analysiert und nach Umsatzpotenzial bewertet.

**Ergebnisse:**
- 🏥 711 Praxen analysiert
- 🎯 145 qualifizierte Premium-Leads
- 📄 20 automatisch generierte PDF-Profile
- 📊 Vollständige CRM-Integration via Google Sheets

---

## Architektur
cat > ~/dental_leads/README.md << 'EOF'
# PraxisScan 🦷

**Automatisiertes B2B Lead Intelligence System für Zahnarztpraxen im DACH-Raum**

Entwickelt im Rahmen von [Arkan Creative](https://github.com/Sam-offger) zur vollautomatischen Kundenakquise.

---

## Was ist PraxisScan?

PraxisScan ist eine vollautomatische Datenpipeline, die Premium-Zahnarztpraxen im DACH-Raum (Deutschland, Österreich, Schweiz) identifiziert, analysiert und nach Umsatzpotenzial bewertet.

**Ergebnisse:**
- 🏥 711 Praxen analysiert
- 🎯 145 qualifizierte Premium-Leads
- 📄 20 automatisch generierte PDF-Profile
- 📊 Vollständige CRM-Integration via Google Sheets

---

## Architektur
```
Discovery → Enrichment → AI Profiling → Scoring → Export
   │              │             │            │          │
Serper API    Jameda         Gemini       0-100     Google
Google Maps   Instagram      2.5 Flash   Scoring    Sheets
              Google Reviews                        + PDF
```

---

## Features

### 🔍 Multi-Source Discovery
- Web-Scraping via Serper API, Jameda und Google Maps
- 52 gezielte Suchanfragen für Premium-Zahnarztpraxen
- Automatischer Junk-Filter für nicht-relevante Domains

### 🤖 KI-Profiling mit Google Gemini 2.5 Flash
- Automatische Positionierungsanalyse jeder Praxis
- Pain-Point-Erkennung (kein Instagram, wenig Reviews etc.)
- Personalisierter Outreach-Winkel pro Lead

### 📊 Social Media Enrichment
- Instagram-Follower-Anzahl und Post-Frequenz
- Google Reviews via Maps API (Rating + Anzahl)
- Owner-Name-Extraktion aus Impressum

### 🎯 Opportunity Scoring (0–100)
| Kriterium | Punkte |
|---|---|
| Kein Instagram / unter 500 Follower | 35 |
| Unter 50 Google Reviews | 25 |
| Kein Marketing-Tracking | 20 |
| Premium-Positionierung | 15 |
| Schweiz-Bonus | 5 |

### 📤 Automatischer Export
- Google Sheets CRM via OAuth2 (Top Leads / Review Queue / Alle)
- PDF-Profile für Top-Leads (ReportLab)
- CSV-Export

---

## Tech Stack

| Bereich | Technologie |
|---|---|
| Sprache | Python 3.11 |
| Datenbank | SQLite |
| KI | Google Gemini 2.5 Flash |
| Scraping | Serper API, BeautifulSoup |
| Export | Google Sheets API, ReportLab |
| Versionierung | Git + GitHub |

---

## Installation
```bash
git clone https://github.com/Sam-offger/praxisscan.git
cd praxisscan
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# API Keys in .env eintragen
```

---

## Verwendung
```bash
# Komplette Pipeline
python cli.py discover
python cli.py enrich
python cli.py profile
python cli.py score

# Social Media & Scoring
python enricher_social.py
python opportunity_scorer.py

# Export
python cli.py export
python sheets_oauth.py

# Stats
python cli.py stats
```

---

## Projektstruktur
```
praxisscan/
├── pipeline.py          # Haupt-Pipeline
├── cli.py               # Command Line Interface
├── db.py                # Datenbankschicht (SQLite)
├── enricher_social.py   # Instagram + Google Reviews
├── enricher_owner.py    # Inhaber-Extraktion
├── opportunity_scorer.py# Scoring-Algorithmus
├── ai_profiler_gemini.py# Gemini AI Integration
├── profile_pdf_generator.py # PDF-Generator
├── sheets_oauth.py      # Google Sheets Export
├── providers/           # Discovery-Provider
├── .env.example         # Konfigurationsvorlage
└── requirements.txt
```

---

## Entwickler

**Sami Adam Moughli** – Gründer Arkan Creative  
Gebaut als internes Tool zur automatisierten B2B-Kundenakquise.

