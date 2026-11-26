"""Stable keyed patient pseudonyms. Secrets are supplied by the caller, never persisted."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from collections.abc import Mapping, Sequence

_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _secret_bytes(secret: str | bytes | None) -> bytes:
    if secret is None:
        secret = os.environ.get("RAKSHA_SECRET", "")
    key = secret.encode("utf-8") if isinstance(secret, str) else bytes(secret)
    if len(key) < 16:
        raise ValueError("RAKSHA_SECRET must contain at least 16 bytes")
    return key


def canonical_patient_key(patient_cluster: object) -> str:
    """Create a deterministic internal cluster key from supplied identity clues."""
    if isinstance(patient_cluster, str):
        material: object = patient_cluster
    elif isinstance(patient_cluster, Mapping):
        material = patient_cluster.get("identity_clues", patient_cluster)
    elif isinstance(patient_cluster, Sequence):
        members = [canonical_patient_key(x) for x in patient_cluster]
        material = sorted(members)
    else:
        material = patient_cluster
    payload = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def generate_patient_id(patient_cluster: object, secret: str | bytes | None = None) -> str:
    """Return a deterministic opaque ID; identical cluster + secret yields identical ID."""
    key = _secret_bytes(secret)
    canonical = canonical_patient_key(patient_cluster)
    digest = hmac.new(key, b"secret-wards:patient:v1:" + canonical.encode("ascii"), hashlib.sha256).digest()
    n = int.from_bytes(digest[:5], "big")
    code = "".join(_ALPHABET[(n >> (5 * i)) & 31] for i in range(6))
    return f"PSN-{code}"
