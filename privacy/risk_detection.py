"""Small, dependency-free quasi-identifier risk measurement and suppression."""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

DEFAULT_QI = ("age", "age_band", "gender", "sex", "district", "location", "admission_date", "diagnosis")


def _get(row: Mapping[str, Any], key: str) -> Any:
    if key in row:
        return row[key]
    clues = row.get("identity_clues")
    if isinstance(clues, Mapping) and key in clues:
        return clues[key]
    return None


def measure_privacy_risk(dataset: Sequence[Mapping[str, Any]], quasi_identifiers: Sequence[str] = DEFAULT_QI,
                         min_group_size: int = 5) -> dict[str, Any]:
    """Return equivalence-class sizes and the fraction of records below k.

    This is a k-anonymity diagnostic, not a guarantee against auxiliary data or
    attribute disclosure. Values are summarized without emitting row contents.
    """
    if min_group_size < 2:
        raise ValueError("min_group_size must be at least 2")
    groups = Counter(tuple(str(_get(r, k) or "") for k in quasi_identifiers) for r in dataset)
    sizes = list(groups.values())
    unsafe = sum(n for n in sizes if n < min_group_size)
    return {
        "records": len(dataset),
        "equivalence_classes": len(groups),
        "minimum_class_size": min(sizes, default=0),
        "records_below_k": unsafe,
        "fraction_below_k": (unsafe / len(dataset)) if dataset else 0.0,
        "k": min_group_size,
    }


def suppress_rare_values(dataset: Sequence[Mapping[str, Any]], quasi_identifiers: Sequence[str] = DEFAULT_QI,
                         min_group_size: int = 5, marker: str = "[SUPPRESSED]") -> list[dict[str, Any]]:
    """Copy records and suppress QI values for records in groups smaller than k."""
    rows = [dict(r) for r in dataset]
    counts = Counter(tuple(str(_get(r, k) or "") for k in quasi_identifiers) for r in rows)
    for row in rows:
        key = tuple(str(_get(row, k) or "") for k in quasi_identifiers)
        if counts[key] >= min_group_size:
            continue
        for field in quasi_identifiers:
            if field in row:
                row[field] = marker
            elif isinstance(row.get("identity_clues"), dict) and field in row["identity_clues"]:
                row["identity_clues"][field] = marker
    return rows
