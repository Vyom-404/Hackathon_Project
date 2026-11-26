"""Permission-restricted temporary storage with authenticated encryption.

The encrypted-file helper uses an HMAC-SHA256-derived keystream and encrypt-then-MAC
with independent derived keys. It is intended for short-lived local intermediates;
prefer an OS keyring or a reviewed AEAD library when one is available.
The caller must provide a secret and explicitly remove temporary files.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import tempfile
from pathlib import Path


def _keys(secret: str | bytes) -> tuple[bytes, bytes]:
    raw = secret.encode() if isinstance(secret, str) else bytes(secret)
    if len(raw) < 16:
        raise ValueError("storage secret must contain at least 16 bytes")
    return (hmac.new(raw, b"secret-wards:enc:v1", hashlib.sha256).digest(),
            hmac.new(raw, b"secret-wards:mac:v1", hashlib.sha256).digest())


def encrypt_bytes(data: bytes, secret: str | bytes) -> bytes:
    enc_key, mac_key = _keys(secret)
    nonce = secrets.token_bytes(16)
    stream = bytearray()
    counter = 0
    while len(stream) < len(data):
        stream.extend(hmac.new(enc_key, nonce + counter.to_bytes(8, "big"), hashlib.sha256).digest())
        counter += 1
    cipher = bytes(a ^ b for a, b in zip(data, stream))
    body = b"SW1" + nonce + cipher
    return body + hmac.new(mac_key, body, hashlib.sha256).digest()


def decrypt_bytes(blob: bytes, secret: str | bytes) -> bytes:
    if len(blob) < 51 or blob[:3] != b"SW1":
        raise ValueError("invalid encrypted payload")
    enc_key, mac_key = _keys(secret)
    body, tag = blob[:-32], blob[-32:]
    if not hmac.compare_digest(tag, hmac.new(mac_key, body, hashlib.sha256).digest()):
        raise ValueError("encrypted payload authentication failed")
    nonce, cipher = body[3:19], body[19:]
    stream = bytearray()
    counter = 0
    while len(stream) < len(cipher):
        stream.extend(hmac.new(enc_key, nonce + counter.to_bytes(8, "big"), hashlib.sha256).digest())
        counter += 1
    return bytes(a ^ b for a, b in zip(cipher, stream))


def write_encrypted_temp(data: bytes, secret: str | bytes, directory: str | os.PathLike[str] | None = None) -> Path:
    """Create a mode-0600 encrypted temporary file. It is not auto-deleted."""
    fd, name = tempfile.mkstemp(prefix="sw-", suffix=".enc", dir=directory)
    path = Path(name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(encrypt_bytes(data, secret))
        return path
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        path.unlink(missing_ok=True)
        raise
