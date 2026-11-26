from __future__ import annotations

from typing import Any

from .pii_detector import detect_pii
from .transliteration import normalize_name


def extract_identity_clues(record: Any) -> dict[str, list[str] | str | None]:
    """Extract in-memory identity evidence from nested JSON/CSV-style data."""
    clues: dict[str, list[str] | str | None] = {
        "names": [],
        "phones": [],
        "identifiers": [],
        "relatives": [],
        "age": None,
        "location": None,
    }

    def walk(value: Any, key_hint: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                hint = f"{key_hint}.{key}" if key_hint else str(key)
                walk(child, hint)
            return
        if isinstance(value, list):
            for child in value:
                walk(child, key_hint)
            return
        if not isinstance(value, str) or not value:
            return

        lower_hint = key_hint.lower()
        detections = detect_pii(value)
        for span in detections:
            raw = value[span.start:span.end]
            if span.entity_type == "PHONE":
                clues["phones"].append(raw)  # type: ignore[union-attr]
            elif span.entity_type in {"RELATIVE_NAME"}:
                clues["relatives"].append(raw)  # type: ignore[union-attr]
            elif span.entity_type in {"PATIENT_NAME", "NAME"}:
                clues["names"].append(raw)  # type: ignore[union-attr]
            elif span.entity_type not in {"ADDRESS", "DOB", "EMAIL"}:
                clues["identifiers"].append(raw)  # type: ignore[union-attr]

        if any(term in lower_hint for term in ("name", "patient", "mareez")) and not detections:
            if "relative" not in lower_hint and "doctor" not in lower_hint:
                clues["names"].append(value)  # type: ignore[union-attr]
        elif "relative" in lower_hint or "s/o" in lower_hint or "w/o" in lower_hint:
            clues["relatives"].append(value)  # type: ignore[union-attr]

        if "age" in lower_hint and isinstance(value, str):
            clues["age"] = value
        if any(term in lower_hint for term in ("village", "district", "address", "location")):
            if not clues["location"]:
                clues["location"] = value

    walk(record)
    for field in ("names", "phones", "identifiers", "relatives"):
        items = clues[field]
        if isinstance(items, list):
            clues[field] = list(dict.fromkeys(items))
    return clues
