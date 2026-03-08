"""
ai_profiler.py – AI profiling of dental practices.

Provider hierarchy:
  1. Ollama (local LLM, free) – default
  2. OpenAI API (if key present)
  3. Anthropic API (if key present)
  4. Rule-based fallback (always works, no LLM needed)

Output is always a fixed JSON schema.
"""
import json
import re
import logging
from typing import Any, Dict, Optional

import httpx

import config

logger = logging.getLogger(__name__)

PROFILE_SCHEMA = {
    "positioning": "",            # "premium" | "mid-range" | "unclear"
    "positioning_reason": "",     # 1-2 sentences
    "service_focus": [],          # list of main services
    "target_patients": "",        # description of likely patient profile
    "pain_points": [],            # list: marketing/branding/conversion/etc
    "outreach_angle": "",         # 1-2 sentences: best hook for outreach
    "summary": "",                # max 120 words
    "profiler": "",               # which provider was used
}

SYSTEM_PROMPT = """You are a B2B sales analyst specializing in premium dental practices (DACH region).
Analyze the provided website text and return ONLY valid JSON (no markdown, no explanation) matching this schema exactly:
{
  "positioning": "premium|mid-range|unclear",
  "positioning_reason": "string (1-2 sentences)",
  "service_focus": ["service1", "service2"],
  "target_patients": "string",
  "pain_points": ["marketing_gap|branding_gap|conversion_gap|reputation_gap|recruiting_gap|premium_conversion_gap"],
  "outreach_angle": "string (1-2 sentences, what to say in first contact)",
  "summary": "string (max 120 words)"
}
Rules:
- Be objective and evidence-based.
- Do NOT infer religion, ethnicity, or any sensitive personal attributes.
- Only list pain_points that are evidenced by the text.
- If information is missing, say "unclear" or leave list empty.
- All output in English.
"""

USER_PROMPT_TEMPLATE = """Website text from a dental practice:
Domain: {domain}
Practice name: {practice_name}
Premium signals found: {premium_signals}
Tracking tags: {tracking}
Conversion signals: {conversion}
Hiring: {hiring}
Team size proxy: {team_size}
Social platforms present: {socials}

Website text (first 3000 chars):
{text}

Return ONLY the JSON object."""


def _build_prompt(extracted: Dict[str, Any]) -> str:
    return USER_PROMPT_TEMPLATE.format(
        domain=extracted.get("domain", ""),
        practice_name=extracted.get("practice_name", ""),
        premium_signals=", ".join(extracted.get("premium_service_signals", [])),
        tracking=", ".join(extracted.get("tracking_tags", [])),
        conversion=", ".join(extracted.get("conversion_signals", [])),
        hiring=str(extracted.get("hiring_signal", False)),
        team_size=str(extracted.get("team_size_proxy", {})),
        socials=", ".join(extracted.get("social_links", {}).keys()),
        text=extracted.get("raw_text_snippet", "")[:3000],
    )


def _parse_json_response(raw: str) -> Dict[str, Any]:
    """Extract JSON from LLM response, handling markdown fences."""
    raw = raw.strip()
    # Remove markdown code fences if present
    raw = re.sub(r"^```(?:json)?", "", raw, flags=re.M).strip()
    raw = re.sub(r"```$", "", raw, flags=re.M).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse failed: {e}. Raw: {raw[:200]}")
        return {}


# ── Provider: Ollama ──────────────────────────────────────────────────────────

def _profile_ollama(extracted: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        client = httpx.Client(timeout=120)
        payload = {
            "model": config.OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_prompt(extracted)},
            ],
            "stream": False,
        }
        resp = client.post(f"{config.OLLAMA_HOST}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("message", {}).get("content", "")
        result = _parse_json_response(content)
        if result:
            result["profiler"] = f"ollama:{config.OLLAMA_MODEL}"
            return result
    except Exception as e:
        logger.warning(f"Ollama profiling failed: {e}")
    return None


# ── Provider: OpenAI ──────────────────────────────────────────────────────────

def _profile_openai(extracted: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not config.OPENAI_API_KEY:
        return None
    try:
        client = httpx.Client(
            timeout=60,
            headers={
                "Authorization": f"Bearer {config.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
        )
        payload = {
            "model": config.OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_prompt(extracted)},
            ],
            "temperature": 0.2,
            "max_tokens": 800,
        }
        resp = client.post("https://api.openai.com/v1/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        result = _parse_json_response(content)
        if result:
            result["profiler"] = f"openai:{config.OPENAI_MODEL}"
            return result
    except Exception as e:
        logger.warning(f"OpenAI profiling failed: {e}")
    return None


# ── Provider: Anthropic ───────────────────────────────────────────────────────

def _profile_anthropic(extracted: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not config.ANTHROPIC_API_KEY:
        return None
    try:
        client = httpx.Client(
            timeout=60,
            headers={
                "x-api-key": config.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
        )
        payload = {
            "model": config.ANTHROPIC_MODEL,
            "max_tokens": 800,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": _build_prompt(extracted)}],
        }
        resp = client.post("https://api.anthropic.com/v1/messages", json=payload)
        resp.raise_for_status()
        data = resp.json()
        content = data["content"][0]["text"]
        result = _parse_json_response(content)
        if result:
            result["profiler"] = f"anthropic:{config.ANTHROPIC_MODEL}"
            return result
    except Exception as e:
        logger.warning(f"Anthropic profiling failed: {e}")
    return None


# ── Provider: Rule-based fallback ─────────────────────────────────────────────

def _profile_rules(extracted: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic rule-based profiling. Always works without any LLM.
    Less nuanced but produces a valid schema.
    """
    premium_signals = extracted.get("premium_service_signals", [])
    tracking = extracted.get("tracking_tags", [])
    conversion = extracted.get("conversion_signals", [])
    hiring = extracted.get("hiring_signal", False)
    socials = extracted.get("social_links", {})
    text_lower = extracted.get("raw_text_snippet", "").lower()

    # Positioning
    high_premium_count = sum(1 for kw in [
        "veneers", "all-on-4", "smile makeover", "vollnarkose", "premium", "privatpraxis"
    ] if kw in text_lower)

    if high_premium_count >= 2:
        positioning = "premium"
        pos_reason = f"Website mentions {high_premium_count} premium service keywords including high-value treatments."
    elif high_premium_count == 1:
        positioning = "mid-range"
        pos_reason = "Some premium signals but not dominant positioning."
    else:
        positioning = "unclear"
        pos_reason = "No clear premium positioning signals detected."

    # Pain points
    pain_points = []
    if not tracking:
        pain_points.append("marketing_gap")
    if not socials:
        pain_points.append("branding_gap")
    if not conversion:
        pain_points.append("conversion_gap")
    if len(socials) <= 1:
        pain_points.append("social_media_gap")

    # Services
    service_map = {
        "implantate": "Implantologie",
        "implants": "Implantologie",
        "veneers": "Veneers",
        "all-on-4": "All-on-4",
        "invisalign": "Invisalign",
        "smile makeover": "Smile Makeover",
        "vollnarkose": "Vollnarkose / Sedierung",
        "sedierung": "Sedierung",
        "zahnästhetik": "Zahnästhetik",
        "cosmetic dentistry": "Cosmetic Dentistry",
    }
    services = [v for k, v in service_map.items() if k in text_lower]

    # Outreach angle
    if "marketing_gap" in pain_points and positioning == "premium":
        angle = "This premium practice appears to lack digital marketing infrastructure. Strong case for patient acquisition optimization."
    elif "conversion_gap" in pain_points:
        angle = "The practice has quality signals but weak online booking/conversion setup – ideal conversation starter."
    else:
        angle = "Established practice with growth potential in digital channels."

    # Summary
    summary = (
        f"{extracted.get('practice_name', 'This practice')} is positioned as {positioning}. "
        f"Key services: {', '.join(services[:3]) or 'general dentistry'}. "
        f"Digital footprint gaps: {', '.join(pain_points[:3]) or 'none identified'}. "
        f"Hiring active: {hiring}. "
        f"Tracking setup: {', '.join(tracking) or 'none detected'}."
    )

    return {
        "positioning": positioning,
        "positioning_reason": pos_reason,
        "service_focus": services,
        "target_patients": "Private patients / premium segment (inferred from service mix)",
        "pain_points": pain_points,
        "outreach_angle": angle,
        "summary": summary[:500],
        "profiler": "rules_fallback",
    }


# ── Main entry point ──────────────────────────────────────────────────────────

def profile_lead(extracted: Dict[str, Any]) -> Dict[str, Any]:
    """
    Profile a lead using the configured AI provider.
    Falls back down the chain until something works.
    """
    provider = config.AI_PROVIDER.lower()

    result = None

    if provider == "ollama":
        result = _profile_ollama(extracted)
        if not result and config.OPENAI_API_KEY:
            logger.info("Ollama failed, trying OpenAI...")
            result = _profile_openai(extracted)
        if not result and config.ANTHROPIC_API_KEY:
            logger.info("OpenAI failed, trying Anthropic...")
            result = _profile_anthropic(extracted)

    elif provider == "openai":
        result = _profile_openai(extracted)

    elif provider == "anthropic":
        result = _profile_anthropic(extracted)

    elif provider == "rules":
        result = _profile_rules(extracted)

    # Always fallback to rules
    if not result:
        logger.info("All LLM providers failed. Using rule-based fallback.")
        result = _profile_rules(extracted)

    # Merge with schema defaults to ensure all keys present
    final = {**PROFILE_SCHEMA, **result}
    return final
