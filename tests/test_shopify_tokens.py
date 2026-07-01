from datetime import datetime, timedelta, timezone

import pytest

from app import shopify_client as sc


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        pass

    def json(self):
        return self.body


class FakeAsyncClient:
    calls = []

    def __init__(self, timeout):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, data=None, headers=None, json=None):
        self.calls.append({"url": url, "data": data, "headers": headers, "json": json})
        return FakeResponse({
            "access_token": "shpat_expiring",
            "expires_in": 3600,
            "refresh_token": "shprt_refresh",
            "refresh_token_expires_in": 7776000,
            "scope": "read_products,read_inventory,read_orders",
        })


@pytest.mark.anyio
async def test_code_exchange_requests_expiring_offline_token(monkeypatch):
    FakeAsyncClient.calls = []
    monkeypatch.setattr(sc.httpx, "AsyncClient", FakeAsyncClient)

    token_fields = await sc.exchange_code_for_token("acme.myshopify.com", "code")

    assert FakeAsyncClient.calls[0]["data"]["expiring"] == "1"
    assert token_fields["token"] == "shpat_expiring"
    assert token_fields["refresh_token"] == "shprt_refresh"
    assert token_fields["token_expires_at"]


@pytest.mark.anyio
async def test_refresh_expiring_offline_token_stores_metadata(monkeypatch):
    FakeAsyncClient.calls = []
    monkeypatch.setattr(sc.httpx, "AsyncClient", FakeAsyncClient)

    token_fields = await sc.refresh_expiring_offline_token(
        "acme.myshopify.com", "old-refresh"
    )

    assert FakeAsyncClient.calls[0]["data"]["grant_type"] == "refresh_token"
    assert FakeAsyncClient.calls[0]["data"]["refresh_token"] == "old-refresh"
    assert token_fields["token"] == "shpat_expiring"
    assert token_fields["refresh_token"] == "shprt_refresh"


def test_token_needs_refresh_uses_stored_expiry():
    soon = datetime.now(timezone.utc) + timedelta(seconds=120)
    later = datetime.now(timezone.utc) + timedelta(hours=2)

    assert sc.token_needs_refresh({
        "refresh_token": "refresh",
        "token_expires_at": soon.isoformat(),
    })
    assert not sc.token_needs_refresh({
        "refresh_token": "refresh",
        "token_expires_at": later.isoformat(),
    })
