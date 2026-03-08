"""
email_generator.py – Generiert personalisierte Outreach-Emails per Lead.
Sprachen: Deutsch + Englisch
Format: Ausführlich & professionell (1 Seite)
"""
import json
import csv
import sqlite3
import httpx
import time
from pathlib import Path
from datetime import datetime

import config

SYSTEM_PROMPT_DE = """Du bist ein erfahrener B2B Sales-Experte für digitales Marketing im Dentalbereich.
Schreibe eine professionelle, personalisierte Outreach-Email auf Deutsch.

Regeln:
- Ton: professionell, respektvoll, nicht aufdringlich
- Länge: 200-250 Wörter (1 Seite)
- Struktur: Betreff + Anrede + Hook (spezifisch zur Praxis) + Problemdarstellung + Lösung + CTA
- Kein generisches "Ich schreibe Ihnen weil..." 
- Beziehe dich konkret auf die Praxis (Name, Services, Stadt)
- CTA: Kurzes 15-Minuten Gespräch vorschlagen
- Absender: Sami (digitaler Marketing-Berater für Premium-Zahnarztpraxen)
- NIEMALS sensible Merkmale erwähnen
Gib NUR die Email zurück, kein Kommentar davor oder danach.
Format:
BETREFF: [Betreff hier]

[Email-Text hier]"""

SYSTEM_PROMPT_EN = """You are an experienced B2B sales expert for digital marketing in the dental sector.
Write a professional, personalized outreach email in English.

Rules:
- Tone: professional, respectful, not pushy
- Length: 200-250 words (1 page)
- Structure: Subject + Greeting + Hook (specific to practice) + Problem + Solution + CTA
- No generic "I am writing to you because..."
- Reference the practice specifically (name, services, city)
- CTA: Suggest a short 15-minute call
- Sender: Sami (digital marketing consultant for premium dental practices)
- NEVER mention sensitive attributes
Return ONLY the email, no commentary before or after.
Format:
SUBJECT: [subject here]

[Email text here]"""

USER_PROMPT_TEMPLATE = """
Praxis-Informationen:
- Name: {name}
- Domain: {domain}
- Stadt: {city}
- Positionierung: {positioning}
- Hauptservices: {services}
- Pain Points: {pain_points}
- Outreach Angle: {angle}
- Tracking vorhanden: {tracking}
- Social Media: {socials}
- Hiring aktiv: {hiring}
- Zusammenfassung: {summary}

Schreibe jetzt die Email.
"""

def generate_email(lead: dict, language: str = "de") -> dict:
    """Generiert eine Outreach-Email für einen Lead."""
    system = SYSTEM_PROMPT_DE if language == "de" else SYSTEM_PROMPT_EN

    # Services parsen
    services = lead.get("service_focus", "[]")
    if isinstance(services, str):
        try:
            services = json.loads(services)
        except Exception:
            services = []

    pain_points = lead.get("pain_points", "[]")
    if isinstance(pain_points, str):
        try:
            pain_points = json.loads(pain_points)
        except Exception:
            pain_points = []

    socials = lead.get("social_links", "{}")
    if isinstance(socials, str):
        try:
            socials = list(json.loads(socials).keys())
        except Exception:
            socials = []

    tracking = lead.get("tracking_tags", "[]")
    if isinstance(tracking, str):
        try:
            tracking = json.loads(tracking)
        except Exception:
            tracking = []

    user_prompt = USER_PROMPT_TEMPLATE.format(
        name=lead.get("practice_name", lead.get("domain", "")),
        domain=lead.get("domain", ""),
        city=lead.get("city", "unbekannt"),
        positioning=lead.get("positioning", "unclear"),
        services=", ".join(services[:5]) if services else "Allgemeine Zahnmedizin",
        pain_points=", ".join(pain_points[:3]) if pain_points else "keine identifiziert",
        angle=lead.get("outreach_angle", ""),
        tracking=", ".join(tracking) if tracking else "keines",
        socials=", ".join(socials) if socials else "keine",
        hiring="Ja" if lead.get("hiring_signal") else "Nein",
        summary=lead.get("summary", "")[:300],
    )

    # Ollama aufrufen
    try:
        client = httpx.Client(timeout=120)
        resp = client.post(
            f"{config.OLLAMA_HOST}/api/chat",
            json={
                "model": config.OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
            }
        )
        resp.raise_for_status()
        content = resp.json().get("message", {}).get("content", "")

        # Betreff und Body trennen
        lines = content.strip().split("\n")
        subject = ""
        body = content

        for i, line in enumerate(lines):
            if line.upper().startswith("BETREFF:") or line.upper().startswith("SUBJECT:"):
                subject = line.split(":", 1)[1].strip()
                body = "\n".join(lines[i+1:]).strip()
                break

        return {
            "subject": subject,
            "body": body,
            "language": language,
            "generated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        return {
            "subject": "",
            "body": f"Error: {e}",
            "language": language,
            "generated_at": datetime.now().isoformat(),
        }


def generate_all_emails(min_score: int = 30, limit: int = 20):
    """Generiert Emails für alle Top-Leads."""
    conn = sqlite3.connect("data/leads.db")
    conn.row_factory = sqlite3.Row

    leads = conn.execute(
        "SELECT * FROM companies WHERE status = 'scored' AND total_score >= ? ORDER BY total_score DESC LIMIT ?",
        (min_score, limit)
    ).fetchall()
    conn.close()

    print(f"\n✉️  Generiere Emails für {len(leads)} Leads...\n")

    results = []
    for lead in leads:
        lead_dict = dict(lead)
        domain = lead_dict["domain"]
        score = lead_dict["total_score"]
        print(f"  {domain} (Score: {score})")

        # Deutsche Email
        email_de = generate_email(lead_dict, "de")
        time.sleep(1)

        # Englische Email
        email_en = generate_email(lead_dict, "en")
        time.sleep(1)

        results.append({
            "domain": domain,
            "practice_name": lead_dict.get("practice_name", ""),
            "city": lead_dict.get("city", ""),
            "score": score,
            "email_contact": _get_best_email(lead_dict),
            "subject_de": email_de["subject"],
            "email_de": email_de["body"],
            "subject_en": email_en["subject"],
            "email_en": email_en["body"],
        })
        print(f"    ✓ DE + EN generiert")

    # CSV speichern
    output_path = Path("exports/outreach_emails.csv")
    if results:
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)

    print(f"\n✅ {len(results)} Email-Paare gespeichert → exports/outreach_emails.csv")
    return results


def _get_best_email(lead: dict) -> str:
    """Gibt die beste Email-Adresse zurück (domain_email bevorzugt)."""
    emails_raw = lead.get("emails", "[]")
    if isinstance(emails_raw, str):
        try:
            emails = json.loads(emails_raw)
        except Exception:
            return ""
    else:
        emails = emails_raw

    # Domain-Email bevorzugen
    for e in emails:
        if isinstance(e, dict) and e.get("type") == "domain_email" and e.get("status") == "valid":
            return e.get("email", "")
    # Fallback: erste valide Email
    for e in emails:
        if isinstance(e, dict) and e.get("status") == "valid":
            return e.get("email", "")
    return ""


if __name__ == "__main__":
    generate_all_emails(min_score=30, limit=20)
