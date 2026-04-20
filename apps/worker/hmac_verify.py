"""HMAC signature verification for incoming job requests.

Mirrors the TypeScript implementation in packages/shared/src/hmac.ts.
"""
from __future__ import annotations

import hashlib
import hmac
import time
from typing import Final

HMAC_HEADER: Final = "x-research-hub-signature"
HMAC_TIMESTAMP_HEADER: Final = "x-research-hub-timestamp"
HMAC_MAX_SKEW_SECONDS: Final = 300


def sign_payload(secret: str, timestamp: str, body: str) -> str:
    mac = hmac.new(secret.encode("utf-8"), f"{timestamp}.{body}".encode("utf-8"), hashlib.sha256)
    return f"sha256={mac.hexdigest()}"


def verify_signature(
    secret: str,
    timestamp: str,
    body: str,
    signature: str,
    now_seconds: int | None = None,
) -> bool:
    if now_seconds is None:
        now_seconds = int(time.time())
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    if abs(now_seconds - ts) > HMAC_MAX_SKEW_SECONDS:
        return False
    expected = sign_payload(secret, timestamp, body)
    return hmac.compare_digest(expected, signature)
