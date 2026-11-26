"""Deterministic per-patient date shifting that preserves date intervals."""
from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import os
import re
from collections.abc import Mapping
from typing import Any


def _secret_bytes(secret: str | bytes | None) -> bytes:
    if secret is None:
        secret = os.environ.get("RAKSHA_SECRET", "")
    value = secret.encode() if isinstance(secret, str) else bytes(secret)
    if len(value) < 16:
        raise ValueError("RAKSHA_SECRET must contain at least 16 bytes")
    return value


def date_shift_days(patient_key: str, secret: str | bytes | None = None, max_days: int = 180) -> int:
    if max_days < 1:
        raise ValueError("max_days must be positive")
    digest = hmac.new(_secret_bytes(secret), b"secret-wards:date:v1:" + patient_key.encode(), hashlib.sha256).digest()
    offset = int.from_bytes(digest[:8], "big") % (2 * max_days + 1) - max_days
    return offset or max_days


_DATE = re.compile(r"(?<!\d)(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})(?!\d)")


def _shift_string(value: str, offset: int) -> str:
    def sub(match: re.Match[str]) -> str:
        raw = match.group(0)
        try:
            parsed = dt.date.fromisoformat(raw) if "-" in raw else dt.datetime.strptime(raw, "%d/%m/%Y").date()
            shifted = parsed + dt.timedelta(days=offset)
            return shifted.isoformat() if "-" in raw else shifted.strftime("%d/%m/%Y")
        except ValueError:
            return raw
    return _DATE.sub(sub, value)


def shift_patient_dates(record: Any, secret: str | bytes | None = None, patient_key: str | None = None,
                        max_days: int = 180) -> Any:
    """Copy-on-write recursively shifts date strings by one fixed patient offset.

    Unlinked records are returned unchanged. Pass a stable canonical key shared by
    the patient's records; medical values and non-date strings are preserved.
    """
    if not patient_key:
        return record
    delta = date_shift_days(patient_key, secret, max_days)
    def walk(value: Any) -> Any:
        if isinstance(value, str):
            return _shift_string(value, delta)
        if isinstance(value, list):
            return [walk(x) for x in value]
        if isinstance(value, tuple):
            return tuple(walk(x) for x in value)
        if isinstance(value, Mapping):
            return {k: walk(v) for k, v in value.items()}
        if isinstance(value, dt.date):
            return value + dt.timedelta(days=delta)
        return value
    return walk(record)
