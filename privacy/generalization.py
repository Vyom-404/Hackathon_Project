"""Quasi-identifier generalization while leaving medical fields intact."""
from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

_AGE_KEYS = {"age", "patientage", "ageyears", "age_years"}
_PIN_KEYS = {"pin", "pincode", "postalcode", "zip", "zipcode"}
_LOCATION_KEYS = {"village", "mohalla", "address", "street", "locality", "tehsil", "city", "district", "location"}


def _key(s: object) -> str:
    return re.sub(r"[^a-z]", "", str(s).casefold())


def age_band(age: int, width: int = 5) -> str:
    if width < 1 or age < 0:
        raise ValueError("age and band width must be non-negative/positive")
    lo = (age // width) * width
    return f"{lo}-{lo + width - 1}"


def _age(value: Any, width: int) -> Any:
    try:
        n = int(value)
        return age_band(n, width)
    except (ValueError, TypeError):
        return value


def generalize_record(record: Any, age_band_years: int = 5, location_level: str = "district") -> Any:
    """Generalize age, PIN and fine-grained locations; retain diagnoses/labs/medicines.

    ``location_level`` currently supports ``district`` (keep district only) and
    ``region`` (replace administrative location values with a broad marker).
    """
    if location_level not in {"district", "region"}:
        raise ValueError("location_level must be 'district' or 'region'")
    def walk(value: Any, parent: str = "") -> Any:
        if isinstance(value, list):
            return [walk(x, parent) for x in value]
        if isinstance(value, tuple):
            return tuple(walk(x, parent) for x in value)
        if isinstance(value, Mapping):
            return {k: walk(v, _key(k)) for k, v in value.items()}
        if parent in _AGE_KEYS:
            return _age(value, age_band_years)
        if parent in _PIN_KEYS:
            s = re.sub(r"\D", "", str(value))
            return s[:3] + "**" if len(s) == 6 else "[LOCATION]" if s else value
        if parent in _LOCATION_KEYS:
            if location_level == "region":
                return "[REGION]"
            if parent in {"address", "street", "locality", "village", "mohalla", "tehsil", "city", "location"}:
                return "[LOCATION]"
        return value
    return walk(record)
