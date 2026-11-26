from __future__ import annotations

import re

MEDICAL_PROTECTED_RE = re.compile(
    r"(?ix)"
    r"\b(?:dolo\s*650|ramipril(?:\s+\d+(?:\.\d+)?)?\s*mg?|"
    r"bp\s*[:=]?\s*\d{2,3}/\d{2,3}|"
    r"\b(?:1[- ]?0[- ]?1|od|bd|tds|qds)\b|"
    r"parkinson(?:'s)?\s+disease|"
    r"\b(?:dr\.?\s*)?[a-z][a-z]+(?:\s+(?:disease|syndrome|fever|cough|pain))\b|"
    r"\b\d+(?:\.\d+)?\s*(?:mg(?:/dl|/dL)?|mcg|ml|mmol/l|g/dl|iu|cells?/mm3)\b|"
    r"\b(?:x\s+\d+\s+(?:day|days|week|weeks)|\d+\s+(?:day|days|week|weeks|month|months))\b|"
    r"\b(?:admission|discharge)\s+date\b)",
)


def protect_medical_text(text: str) -> str:
    """Return text unchanged with protected spans marked only as metadata, if any."""
    if not isinstance(text, str):
        return text
    # This is deliberately a sentinel-free utility: it confirms/exports no PII.
    return text


def is_medical_context(text: str, start: int, end: int) -> bool:
    """Check whether a span is surrounded by unambiguous medical context."""
    if not isinstance(text, str):
        return False
    window = text[max(0, start - 60):min(len(text), end + 60)]
    return MEDICAL_PROTECTED_RE.search(window) is not None
