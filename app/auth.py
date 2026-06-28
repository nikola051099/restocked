"""
Shopify embedded-app session-token (JWT) verification.

Embedded apps must authenticate every backend request with the session token
App Bridge puts in the Authorization: Bearer header — NOT cookies (third-party
cookies are blocked in the admin iframe). This is a hard app-review requirement.

We verify the HS256 signature with the app's API secret and validate the
standard claims, then return the shop domain from the `dest` claim.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from fastapi import Header, HTTPException

from .config import settings


def _b64url_decode(seg: str) -> bytes:
    pad = "=" * (-len(seg) % 4)
    return base64.urlsafe_b64decode(seg + pad)


def verify_session_token(token: str) -> str:
    """Return the shop domain if the token is valid, else raise HTTPException."""
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
    except ValueError:
        raise HTTPException(401, "Malformed session token")

    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected = hmac.new(settings.API_SECRET.encode(), signing_input,
                        hashlib.sha256).digest()
    if not hmac.compare_digest(expected, _b64url_decode(sig_b64)):
        raise HTTPException(401, "Bad session-token signature")

    payload = json.loads(_b64url_decode(payload_b64))

    now = int(time.time())
    if payload.get("exp", 0) < now - 5:
        raise HTTPException(401, "Session token expired")
    if payload.get("nbf", 0) > now + 5:
        raise HTTPException(401, "Session token not yet valid")
    if payload.get("aud") != settings.API_KEY:
        raise HTTPException(401, "Session token audience mismatch")

    dest = payload.get("dest", "")  # e.g. "https://store.myshopify.com"
    shop = dest.replace("https://", "").replace("http://", "").strip("/")
    if not shop.endswith(".myshopify.com"):
        raise HTTPException(401, "Session token missing shop")
    return shop


async def require_shop(authorization: str = Header(default="")) -> str:
    """FastAPI dependency: enforce a valid session token, return shop domain.
    In DEMO mode auth is bypassed and a demo shop is returned."""
    if settings.DEMO:
        return "demo-store.myshopify.com"
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Missing session token")
    return verify_session_token(authorization.split(" ", 1)[1].strip())
