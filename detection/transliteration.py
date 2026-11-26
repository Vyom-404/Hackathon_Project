from __future__ import annotations

import re
import unicodedata

try:
    import unicodedata2  # type: ignore[import-not-found]
except ImportError:
    unicodedata2 = None


HONORIFIC_RE = re.compile(r"(?iu)^(?:श्री|श्रीमती|smt|mr|mrs|ms|dr|doctor|shri)\s*[., ]*\s*", re.IGNORECASE)
SUFFIX_HONORIFIC_RE = re.compile(r"(?iu)[\s,]*(?:ji|sahab|didi|जी|साहब|दीदी)$", re.IGNORECASE)

VARIANT = {
    "mohammad": "mohammad",
    "mohammed": "mohammad",
    "mohamed": "mohammad",
    "mohd": "mohammad",
    "md": "mohammad",
    "मोहम्मद": "mohammad",
    "मुहम्मद": "mohammad",
}


def normalize_name(name: str) -> str:
    """Normalize a name for consistent comparison; never performs name matching."""
    if not isinstance(name, str):
        return ""
    text = unicodedata.normalize("NFKC", name)
    text = text.strip()
    text = HONORIFIC_RE.sub("", text, count=1)
    text = SUFFIX_HONORIFIC_RE.sub("", text)
    text = re.sub(r"(?u)[^\w\s\u0900-\u097F]", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = text.strip().lower()

    parts = text.split()
    if parts:
        parts = [VARIANT.get(part, part) for part in parts]
    text = " ".join(part for part in parts if len(part) > 1 or part.isalpha())

    # Lightweight transliteration: common syllables used in Indian names.
    transliteration_map = {
        "श": "sh", "ा": "a", "ि": "i", "ी": "i", "ु": "u", "ू": "u",
        "े": "e", "ै": "ai", "ो": "o", "ौ": "au", "क": "k", "ख": "kh",
        "ग": "g", "घ": "gh", "च": "ch", "ज": "j", "ट": "t", "ठ": "th",
        "ड": "d", "ढ": "dh", "त": "t", "थ": "th", "द": "d", "ध": "dh",
        "न": "n", "प": "p", "ब": "b", "भ": "bh", "म": "m", "य": "y",
        "र": "r", "ल": "l", "व": "v", "स": "s", "ह": "h",
    }
    if re.search(r"[ऀ-\u097F]", text):
        result = []
        for char in text:
            result.append(transliteration_map.get(char, char))
        text = "".join(result)
        text = re.sub(r"[.]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_text(text: str) -> str:
    """Remove PII spans from text while retaining surrounding medical content."""
    from .pii_detector import detect_pii

    if not isinstance(text, str):
        return text
    spans = detect_pii(text)
    if not spans:
        return text

    replacements = {
        "PATIENT_NAME": "[NAME]",
        "RELATIVE_NAME": "[RELATIVE]",
        "PHONE": "[PHONE]",
        "AADHAAR": "[AADHAAR]",
        "ABHA": "[ABHA]",
        "PAN": "[PAN]",
        "MRN": "[MRN]",
        "UHID": "[MRN]",
        "INSURANCE_ID": "[INSURANCE_ID]",
        "ADDRESS": "[ADDRESS]",
        "DOB": "[DOB]",
        "EMAIL": "[EMAIL]",
    }
    result: list[str] = []
    cursor = 0
    for span in sorted(spans, key=lambda item: item.start):
        result.append(text[cursor:span.start])
        result.append(replacements.get(span.entity_type, "[REDACTED]"))
        cursor = span.end
    result.append(text[cursor:])
    return "".join(result)
