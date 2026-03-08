import json, logging, os, re
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Du bist Experte für Premium-Zahnarztpraxen im DACH-Raum.
Analysiere die Daten und erstelle ein Profil.
Antworte NUR mit validem JSON, keine Backticks, keine Kommentare.

Schema:
{
  "positioning": "premium" | "mid-range" | "unclear",
  "positioning_reason": "1-2 Sätze",
  "service_focus": ["service1", "service2"],
  "target_patients": "Beschreibung",
  "pain_points": ["marketing_gap", "branding_gap", "conversion_gap", "reputation_gap", "recruiting_gap", "premium_conversion_gap"],
  "outreach_angle": "1-2 Sätze für ersten Kontakt",
  "summary": "max 120 Wörter",
  "profiler": "gemini"
}"""

def profile_with_gemini(extracted: dict) -> dict:
    try:
        from google import genai
        from dotenv import load_dotenv
        load_dotenv(override=True)
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY nicht gesetzt")

        client = genai.Client(api_key=api_key)

        signals = extracted.get("premium_service_signals", [])
        tracking = extracted.get("tracking_tags", [])
        socials = extracted.get("social_links", {})
        affinity = extracted.get("affinity_signals", {})

        prompt = f"""{SYSTEM_PROMPT}

Praxis: {extracted.get('practice_name', 'Unbekannt')}
Domain: {extracted.get('domain', '')}
Stadt: {extracted.get('city', 'unbekannt')}
Land: {extracted.get('country', 'DE')}
Premium-Services: {', '.join(signals[:15]) if signals else 'keine'}
Tracking: {', '.join(tracking) if tracking else 'keines'}
Social Media: {', '.join(socials.keys()) if socials else 'keines'}
Hiring aktiv: {'Ja' if extracted.get('hiring_signal') else 'Nein'}
Email: {'Ja' if extracted.get('emails') else 'Nein'}
Sprach-Signale: {', '.join(affinity.keys()) if affinity else 'keine'}

Erstelle jetzt das JSON-Profil."""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        raw = response.text.strip()
        raw = re.sub(r"```json|```", "", raw).strip()
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            raw = m.group(0)

        profile = json.loads(raw)
        profile["profiler"] = "gemini"
        return profile

    except json.JSONDecodeError as e:
        logger.warning(f"Gemini JSON parse error: {e}")
        return None
    except Exception as e:
        logger.warning(f"Gemini failed: {e}")
        return None
