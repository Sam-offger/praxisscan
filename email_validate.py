"""
email_validate.py – Email validation: syntax + MX DNS check.

Levels:
  valid   – syntax OK + MX record found
  invalid – syntax bad OR known junk domain
  unknown – syntax OK but no MX found (domain might be down)
"""
import re
import logging
from typing import Dict, List

import dns.resolver

logger = logging.getLogger(__name__)

EMAIL_SYNTAX_RE = re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
)

JUNK_DOMAINS = {
    "example.com", "test.com", "mailinator.com", "guerrillamail.com",
    "tempmail.com", "yopmail.com", "trashmail.com", "sharklasers.com",
    "schema.org", "w3.org", "sentry.io",
}

_mx_cache: Dict[str, bool] = {}


def _check_mx(domain: str) -> bool:
    if domain in _mx_cache:
        return _mx_cache[domain]
    try:
        answers = dns.resolver.resolve(domain, "MX", lifetime=5)
        result = len(answers) > 0
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.Timeout,
            dns.resolver.NoNameservers, Exception):
        result = False
    _mx_cache[domain] = result
    return result


def validate_email(email: str) -> Dict[str, str]:
    email = email.strip().lower()

    # Syntax check
    if not EMAIL_SYNTAX_RE.match(email):
        return {"email": email, "status": "invalid", "reason": "syntax_error"}

    domain = email.split("@")[1]

    # Junk domain check
    if domain in JUNK_DOMAINS:
        return {"email": email, "status": "invalid", "reason": "junk_domain"}

    # MX check
    if _check_mx(domain):
        return {"email": email, "status": "valid", "reason": "mx_found"}
    else:
        return {"email": email, "status": "unknown", "reason": "no_mx_record"}


def validate_email_list(emails: List[Dict]) -> List[Dict]:
    """
    Takes list of {email: str, type: str} dicts,
    returns them with added validation status.
    """
    results = []
    for item in emails:
        v = validate_email(item["email"])
        results.append({**item, **v})
    return results
