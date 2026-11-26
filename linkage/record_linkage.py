"""Conservative patient matching over detector-produced identity clues.

Expected record shape is the PRD's internal record mapping, with identity clues
under ``identity_clues`` (names, phones, identifiers, relatives, age, location).
Aliases such as ``patient_name``, ``phone`` and ``uhid`` are accepted for easy
integration with heterogeneous parsers. Medical fields are never used as match
evidence.
"""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any, Iterable, Mapping

_ALIASES = {
    "names": ("names", "name", "patient_name", "patient", "full_name"),
    "phones": ("phones", "phone", "mobile", "phone_number"),
    "identifiers": ("identifiers", "identifier", "uhid", "mrn", "patient_id", "abha", "aadhaar"),
    "relatives": ("relatives", "relative", "relative_name", "guardian", "father_name", "mother_name"),
}


def normalize_name(value: Any) -> str:
    """Normalize Latin/Devanagari names consistently without network resources."""
    s = unicodedata.normalize("NFKC", str(value or "")).casefold()
    s = re.sub(r"^(?:mr|mrs|ms|श्री|श्रीमती|कुमारी|श्रीमान)\.?\s+", "", s)
    s = re.sub(r"\b(?:ji|sahab|sahib|didi|bhai)\b", " ", s)
    return " ".join(re.findall(r"[a-z0-9]+|[\u0900-\u097f]+", s))


def _identity(record: Mapping[str, Any]) -> Mapping[str, Any]:
    clues = record.get("identity_clues")
    return clues if isinstance(clues, Mapping) else record


def _values(record: Mapping[str, Any], group: str) -> set[str]:
    obj = _identity(record)
    vals: set[str] = set()
    for key in _ALIASES[group]:
        if key not in obj:
            continue
        raw = obj[key]
        seq = raw if isinstance(raw, (list, tuple, set)) else [raw]
        for v in seq:
            if v is None:
                continue
            if group == "names" or group == "relatives":
                n = normalize_name(v)
            elif group == "phones":
                n = "".join(re.findall(r"\d", str(v)))[-10:]
            else:
                n = re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKC", str(v)).casefold())
            if len(n) >= (7 if group == "phones" else 3):
                vals.add(n)
    return vals


def _scalar(record: Mapping[str, Any], key: str) -> Any:
    obj = _identity(record)
    if key in obj:
        return obj[key]
    return record.get(key)


def compare_patients(record1: Mapping[str, Any], record2: Mapping[str, Any]) -> bool:
    """Return True only when identity evidence is strong enough to link.

    A matching normalized phone or identifier is strong evidence, provided no
    competing explicit identifiers conflict. Name-only and demographic-only
    matches are deliberately insufficient.
    """
    ids1, ids2 = _values(record1, "identifiers"), _values(record2, "identifiers")
    phones1, phones2 = _values(record1, "phones"), _values(record2, "phones")
    if ids1 and ids2 and ids1.isdisjoint(ids2):
        return False
    if phones1 and phones2 and phones1.isdisjoint(phones2) and not (ids1 & ids2):
        return False
    if ids1 & ids2 or phones1 & phones2:
        return True

    names1, names2 = _values(record1, "names"), _values(record2, "names")
    rel1, rel2 = _values(record1, "relatives"), _values(record2, "relatives")
    # Fuzzy names are accepted only with matching relative-name evidence and
    # age agreement (when age is available). This reduces homonym merges.
    same_relative = bool(rel1 & rel2)
    age1, age2 = _scalar(record1, "age"), _scalar(record2, "age")
    try:
        age_agrees = age1 is not None and age2 is not None and abs(int(age1) - int(age2)) <= 1
    except (TypeError, ValueError):
        age_agrees = False
    if same_relative and age_agrees and names1 and names2:
        return max(SequenceMatcher(None, a, b).ratio() for a in names1 for b in names2) >= 0.94
    return False


def cluster_records(records: Iterable[Mapping[str, Any]]) -> list[list[int]]:
    """Cluster records using pairwise evidence while preventing contradictory-ID merges.

    The output contains indices into the supplied iterable. Singletons are omitted;
    callers should leave those records unlinked unless they have another trusted key.
    A candidate union is rejected when any cross-cluster pair has conflicting IDs.
    """
    rows = list(records)
    parent = list(range(len(rows)))
    members = [{i} for i in range(len(rows))]

    def root(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def hard_conflict(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
        x, y = _values(a, "identifiers"), _values(b, "identifiers")
        px, py = _values(a, "phones"), _values(b, "phones")
        return bool((x and y and x.isdisjoint(y)) or (px and py and px.isdisjoint(py) and not (x & y)))

    edges = [(i, j) for i in range(len(rows)) for j in range(i + 1, len(rows)) if compare_patients(rows[i], rows[j])]
    for i, j in edges:
        ri, rj = root(i), root(j)
        if ri == rj:
            continue
        if any(hard_conflict(rows[a], rows[b]) for a in members[ri] for b in members[rj]):
            continue
        parent[rj] = ri
        members[ri] |= members[rj]
    groups: dict[int, list[int]] = {}
    for i in range(len(rows)):
        groups.setdefault(root(i), []).append(i)
    return [g for g in groups.values() if len(g) > 1]
