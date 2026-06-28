"""
Mandatory Shopify compliance webhooks (required to pass app review) plus
app/uninstalled cleanup. All verify the HMAC before acting.
"""
from __future__ import annotations

from fastapi import APIRouter, Request, Response

from .shopify_client import verify_webhook
from .store import store

router = APIRouter()


async def _verified_body(request: Request) -> bytes | None:
    raw = await request.body()
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256", "")
    if not verify_webhook(raw, hmac_header):
        return None
    return raw


@router.post("/webhooks/app/uninstalled")
async def app_uninstalled(request: Request):
    raw = await _verified_body(request)
    if raw is None:
        return Response(status_code=401)
    shop = request.headers.get("X-Shopify-Shop-Domain", "")
    if shop:
        store.delete(shop)  # forget the token + data on uninstall
    return Response(status_code=200)


# --- GDPR mandatory webhooks (must exist and return 200/401 correctly) ----- #

@router.post("/webhooks/customers/data_request")
async def customers_data_request(request: Request):
    raw = await _verified_body(request)
    return Response(status_code=200 if raw is not None else 401)


@router.post("/webhooks/customers/redact")
async def customers_redact(request: Request):
    raw = await _verified_body(request)
    # We store no customer PII (only aggregated variant demand), so nothing to redact.
    return Response(status_code=200 if raw is not None else 401)


@router.post("/webhooks/shop/redact")
async def shop_redact(request: Request):
    raw = await _verified_body(request)
    if raw is not None:
        shop = request.headers.get("X-Shopify-Shop-Domain", "")
        if shop:
            store.delete(shop)
        return Response(status_code=200)
    return Response(status_code=401)
