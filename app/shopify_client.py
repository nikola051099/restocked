"""
Shopify OAuth + Admin API (GraphQL) client, with rate-limit handling.

Embedded-app auth uses session tokens (see auth.py). This module handles the
install OAuth handshake and the GraphQL queries we need (orders, variants),
with retry/backoff on Shopify's throttling so big catalogs don't error out.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import secrets
from urllib.parse import urlencode

import httpx

from .config import settings


# ----------------------------- OAuth -------------------------------------- #

def build_install_url(shop: str, state: str) -> str:
    params = {
        "client_id": settings.API_KEY,
        "scope": settings.SCOPES,
        "redirect_uri": settings.redirect_uri,
        "state": state,
    }
    return f"https://{shop}/admin/oauth/authorize?{urlencode(params)}"


def new_state() -> str:
    return secrets.token_urlsafe(24)


def verify_hmac(query_params: dict) -> bool:
    params = dict(query_params)
    received = params.pop("hmac", None)
    if not received:
        return False
    params.pop("signature", None)
    message = "&".join(f"{k}={params[k]}" for k in sorted(params))
    digest = hmac.new(settings.API_SECRET.encode(), message.encode(),
                      hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, received)


def verify_webhook(raw_body: bytes, hmac_header: str) -> bool:
    import base64
    digest = hmac.new(settings.API_SECRET.encode(), raw_body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode()
    return hmac.compare_digest(expected, hmac_header or "")


async def exchange_code_for_token(shop: str, code: str) -> str:
    url = f"https://{shop}/admin/oauth/access_token"
    payload = {"client_id": settings.API_KEY,
               "client_secret": settings.API_SECRET, "code": code}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()
        return r.json()["access_token"]


def required_access_scopes() -> set[str]:
    return {s.strip() for s in settings.SCOPES.split(",") if s.strip()}


async def fetch_access_scopes(shop: str, token: str) -> set[str]:
    url = f"https://{shop}/admin/oauth/access_scopes.json"
    headers = {"X-Shopify-Access-Token": token}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, headers=headers)
        r.raise_for_status()
        body = r.json()
    return {
        item.get("handle")
        for item in body.get("access_scopes", [])
        if item.get("handle")
    }


async def missing_access_scopes(shop: str, token: str) -> set[str]:
    return required_access_scopes() - await fetch_access_scopes(shop, token)


# --------------------------- Admin GraphQL -------------------------------- #

class AdminAPI:
    MAX_RETRIES = 5

    def __init__(self, shop: str, token: str):
        self.shop = shop
        self.token = token
        self.endpoint = f"https://{shop}/admin/api/{settings.API_VERSION}/graphql.json"

    async def _gql(self, query: str, variables: dict | None = None) -> dict:
        headers = {"X-Shopify-Access-Token": self.token,
                   "Content-Type": "application/json"}
        body = {"query": query, "variables": variables or {}}
        backoff = 1.0
        async with httpx.AsyncClient(timeout=60) as client:
            for attempt in range(self.MAX_RETRIES):
                r = await client.post(self.endpoint, headers=headers, json=body)
                # HTTP-level rate limit
                if r.status_code == 429:
                    await asyncio.sleep(float(r.headers.get("Retry-After", backoff)))
                    backoff = min(backoff * 2, 16)
                    continue
                r.raise_for_status()
                data = r.json()
                # GraphQL-level throttling
                if "errors" in data:
                    throttled = any(
                        (e.get("extensions", {}) or {}).get("code") == "THROTTLED"
                        for e in data["errors"]
                    )
                    if throttled and attempt < self.MAX_RETRIES - 1:
                        await asyncio.sleep(backoff)
                        backoff = min(backoff * 2, 16)
                        continue
                    raise RuntimeError(f"GraphQL error: {data['errors']}")
                return data["data"]
        raise RuntimeError("Shopify API throttled after retries")

    async def fetch_orders(self, since_iso: str, page_limit: int = 50) -> list[dict]:
        query = """
        query Orders($cursor: String, $q: String!) {
          orders(first: 100, after: $cursor, query: $q, sortKey: CREATED_AT) {
            edges {
              cursor
              node {
                createdAt
                lineItems(first: 100) {
                  edges { node { quantity variant { id } product { id } } }
                }
              }
            }
            pageInfo { hasNextPage }
          }
        }"""
        nodes, cursor = [], None
        for _ in range(page_limit):
            data = await self._gql(query, {"cursor": cursor,
                                           "q": f"created_at:>={since_iso}"})
            conn = data["orders"]
            for edge in conn["edges"]:
                nodes.append(edge["node"])
                cursor = edge["cursor"]
            if not conn["pageInfo"]["hasNextPage"]:
                break
        return nodes

    async def fetch_variants(
        self,
        page_limit: int = 50,
        include_inventory: bool = True,
    ) -> list[dict]:
        inventory_field = "inventoryQuantity" if include_inventory else ""
        query = f"""
        query Variants($cursor: String) {{
          productVariants(first: 200, after: $cursor) {{
            edges {{
              cursor
              node {{
                id
                {inventory_field}
                selectedOptions {{ name value }}
                product {{ id title }}
              }}
            }}
            pageInfo {{ hasNextPage }}
          }}
        }}"""
        nodes, cursor = [], None
        for _ in range(page_limit):
            data = await self._gql(query, {"cursor": cursor})
            conn = data["productVariants"]
            for edge in conn["edges"]:
                nodes.append(edge["node"])
                cursor = edge["cursor"]
            if not conn["pageInfo"]["hasNextPage"]:
                break
        return nodes

    async def fetch_shop_email(self) -> str:
        query = "{ shop { email contactEmail } }"
        data = await self._gql(query)
        shop = data.get("shop", {}) or {}
        return shop.get("email") or shop.get("contactEmail") or ""
