import base64, hmac, hashlib, json, time
import pytest
from fastapi import HTTPException
from app.auth import verify_session_token
from app.config import settings

def _b64(d): return base64.urlsafe_b64encode(d).decode().rstrip("=")

def mint(secret=None, aud=None, dest="https://acme.myshopify.com", exp_delta=300):
    secret = secret or settings.API_SECRET
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    now = int(time.time())
    payload = _b64(json.dumps({
        "aud": aud or settings.API_KEY, "dest": dest,
        "exp": now + exp_delta, "nbf": now - 10, "iat": now}).encode())
    sig = _b64(hmac.new(secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"

def test_valid_token_returns_shop():
    assert verify_session_token(mint()) == "acme.myshopify.com"

def test_bad_signature_rejected():
    with pytest.raises(HTTPException):
        verify_session_token(mint(secret="wrong-secret"))

def test_expired_token_rejected():
    with pytest.raises(HTTPException):
        verify_session_token(mint(exp_delta=-100))

def test_wrong_audience_rejected():
    with pytest.raises(HTTPException):
        verify_session_token(mint(aud="someone-else"))

def test_malformed_token_rejected():
    with pytest.raises(HTTPException):
        verify_session_token("not.a.jwt.token")
