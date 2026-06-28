"""
FastAPI entrypoint: OAuth install, embedded dashboard, recommendations API,
billing, and cron job endpoints. Hardened for Shopify app review: session-token
auth on data endpoints, CSP frame-ancestors, cached reads + background refresh.

Local demo:  DEMO=1 uvicorn app.main:app --reload
             http://localhost:8000/?shop=demo-store.myshopify.com
"""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException, Depends, Header
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from .config import settings
from . import shopify_client as sc
from .auth import require_shop
from .store import store
from .forecasting import compute_recommendations, build_demo_payload
from .billing import create_subscription, PLANS
from .digest import run_digests
from .webhooks import router as webhook_router
from .legal import router as legal_router

app = FastAPI(title="Variant Forecasting App")
app.include_router(webhook_router)
app.include_router(legal_router)
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

_SHOP_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9\-]*\.myshopify\.com$")


def _valid_shop(shop): return bool(shop and _SHOP_RE.match(shop))
def _clean_lead_time(v): return v if (v and 1 <= v <= 365) else None


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["Content-Security-Policy"] = (
        "frame-ancestors https://admin.shopify.com https://*.myshopify.com;")
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp


@app.get("/healthz")
async def healthz():
    return {"ok": True, "demo": settings.DEMO}


# ----------------------------- OAuth -------------------------------------- #

@app.get("/install")
async def install(shop: str):
    if not _valid_shop(shop):
        raise HTTPException(400, "Invalid shop domain")
    state = sc.new_state()
    data = store.get(shop); data["oauth_state"] = state; store.put(shop, data)
    return RedirectResponse(sc.build_install_url(shop, state))


@app.get("/auth/callback")
async def auth_callback(request: Request):
    params = dict(request.query_params)
    shop = params.get("shop")
    if not _valid_shop(shop):
        raise HTTPException(400, "Invalid shop")
    if not sc.verify_hmac(params):
        raise HTTPException(401, "HMAC verification failed")
    if params.get("state") != store.get(shop).get("oauth_state"):
        raise HTTPException(401, "State mismatch")
    token = await sc.exchange_code_for_token(shop, params["code"])
    data = store.get(shop); data.update(token=token, oauth_state=None); store.put(shop, data)
    host = params.get("host", "")
    if host:
        return RedirectResponse(f"/?shop={shop}&host={host}")
    return RedirectResponse(
        f"https://admin.shopify.com/store/{shop.split('.')[0]}/apps/{settings.API_KEY}")


# --------------------------- Dashboard ------------------------------------ #

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, shop: str | None = None):
    if settings.DEMO and not shop:
        shop = "demo-store.myshopify.com"
    if not _valid_shop(shop):
        return HTMLResponse("<h3>Open this app from your Shopify admin.</h3>"
                            "<p>Or append <code>?shop=yourstore.myshopify.com</code>.</p>")
    if not settings.DEMO and not store.get(shop).get("token"):
        return RedirectResponse(f"/install?shop={shop}")
    return templates.TemplateResponse(request, "dashboard.html", {
        "shop": shop, "api_key": settings.API_KEY,
        "plans": PLANS, "plan": store.get(shop).get("plan"), "demo": settings.DEMO})


# --------------------------- Data API ------------------------------------- #

@app.get("/api/recommendations")
async def api_recommendations(shop: str = Depends(require_shop)):
    if settings.DEMO:
        data = store.get(shop)
        return JSONResponse(data.get("last_run") or build_demo_payload(data.get("lead_time_days")))
    data = store.get(shop)
    if not data.get("token"):
        raise HTTPException(401, "Not installed")
    if data.get("last_run"):
        return JSONResponse(data["last_run"])
    result = await compute_recommendations(shop, data["token"], data.get("lead_time_days"))
    data["last_run"] = result; data["email"] = result.get("shop_email") or data.get("email")
    store.put(shop, data)
    return JSONResponse(result)


@app.post("/api/refresh")
async def api_refresh(shop: str = Depends(require_shop), lead_time: int | None = None):
    lt = _clean_lead_time(lead_time)
    data = store.get(shop)
    if lt:
        data["lead_time_days"] = lt
    if settings.DEMO:
        result = build_demo_payload(data.get("lead_time_days"))
        data["last_run"] = result; store.put(shop, data)
        return JSONResponse(result)
    if not data.get("token"):
        raise HTTPException(401, "Not installed")
    result = await compute_recommendations(shop, data["token"], data.get("lead_time_days"))
    data["last_run"] = result; data["email"] = result.get("shop_email") or data.get("email")
    store.put(shop, data)
    return JSONResponse(result)


# --------------------------- Cron jobs ------------------------------------ #

def _check_cron(secret: str | None):
    if not settings.CRON_SECRET or secret != settings.CRON_SECRET:
        raise HTTPException(401, "Bad cron secret")


@app.post("/tasks/refresh-all")
async def refresh_all(x_cron_secret: str | None = Header(default=None)):
    _check_cron(x_cron_secret)
    done, failed = 0, 0
    for shop in store.all_shops():
        data = store.get(shop)
        if not data.get("token"):
            continue
        try:
            result = await compute_recommendations(shop, data["token"], data.get("lead_time_days"))
            data["last_run"] = result; data["email"] = result.get("shop_email") or data.get("email")
            store.put(shop, data); done += 1
        except Exception:
            failed += 1
    return {"refreshed": done, "failed": failed}


@app.post("/tasks/digest")
async def tasks_digest(x_cron_secret: str | None = Header(default=None)):
    _check_cron(x_cron_secret)
    return run_digests()


# ----------------------------- Billing ------------------------------------ #

@app.get("/billing/subscribe")
async def billing_subscribe(shop: str, plan: str):
    if not _valid_shop(shop) or plan not in PLANS:
        raise HTTPException(400, "Bad request")
    if settings.DEMO:
        return RedirectResponse(f"/?shop={shop}")
    token = store.get(shop).get("token")
    if not token:
        raise HTTPException(401, "Not installed")
    return_url = f"{settings.APP_URL}/billing/callback?shop={shop}&plan={plan}"
    return RedirectResponse(await create_subscription(shop, token, plan, return_url))


@app.get("/billing/callback")
async def billing_callback(shop: str, plan: str):
    if not _valid_shop(shop) or plan not in PLANS:
        raise HTTPException(400, "Bad request")
    store.update(shop, plan=plan)
    return RedirectResponse(f"/?shop={shop}")
