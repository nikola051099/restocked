from fastapi.testclient import TestClient
from app.config import settings
from app import main

app = main.app
c = TestClient(app)

def test_healthz():
    r = c.get("/healthz"); assert r.status_code == 200 and r.json()["ok"] is True

def test_security_header_present():
    r = c.get("/healthz")
    assert "frame-ancestors" in r.headers.get("content-security-policy", "")

def test_dashboard_renders_demo():
    r = c.get("/?shop=demo-store.myshopify.com")
    assert r.status_code == 200 and "Restocked" in r.text

def test_root_fallback_includes_app_bridge_for_scanner(monkeypatch):
    monkeypatch.setattr(settings, "DEMO", False)
    r = c.get("/")
    assert r.status_code == 200
    assert 'meta name="shopify-api-key"' in r.text
    assert "cdn.shopify.com/shopifycloud/app-bridge.js" in r.text

def test_plan_link_breaks_out_of_embedded_iframe(monkeypatch):
    async def fake_missing_scopes(shop, token):
        return set()

    monkeypatch.setattr(settings, "DEMO", False)
    monkeypatch.setattr(main.sc, "missing_access_scopes", fake_missing_scopes)
    main.store.update("acme.myshopify.com", token="token")
    try:
        r = c.get("/?shop=acme.myshopify.com")
    finally:
        main.store.delete("acme.myshopify.com")
    assert r.status_code == 200
    assert 'target="_top"' in r.text

def test_dashboard_redirects_stale_install_for_scope_update(monkeypatch):
    async def fake_missing_scopes(shop, token):
        return {"read_products"}

    monkeypatch.setattr(settings, "DEMO", False)
    monkeypatch.setattr(main.sc, "missing_access_scopes", fake_missing_scopes)
    main.store.update("acme.myshopify.com", token="token")
    try:
        r = c.get("/?shop=acme.myshopify.com", follow_redirects=False)
    finally:
        main.store.delete("acme.myshopify.com")

    assert r.status_code in (302, 307)
    assert r.headers["location"] == "/install?shop=acme.myshopify.com&scope_check=1"

def test_dashboard_does_not_loop_after_scope_update_attempt(monkeypatch):
    async def fake_missing_scopes(shop, token):
        return {"read_products"}

    monkeypatch.setattr(settings, "DEMO", False)
    monkeypatch.setattr(main.sc, "missing_access_scopes", fake_missing_scopes)
    main.store.update("acme.myshopify.com", token="token")
    try:
        r = c.get("/?shop=acme.myshopify.com&scope_checked=1")
    finally:
        main.store.delete("acme.myshopify.com")

    assert r.status_code == 200
    assert "Restocked" in r.text

def test_recommendations_demo():
    r = c.get("/api/recommendations?shop=demo-store.myshopify.com")
    assert r.status_code == 200
    d = r.json(); assert len(d["recommendations"]) == 10
    assert d["recommendations"][0]["stockout_risk"] == "imminent"

def test_refresh_lead_time_changes_qty():
    a = c.post("/api/refresh?shop=demo-store.myshopify.com&lead_time=14").json()
    b = c.post("/api/refresh?shop=demo-store.myshopify.com&lead_time=90").json()
    pick = lambda p: [x for x in p["recommendations"] if x["size"]=="M" and x["color"]=="Black"][0]["recommended_order_qty"]
    assert pick(b) > pick(a)

def test_cron_requires_secret():
    assert c.post("/tasks/refresh-all").status_code == 401
    assert c.post("/tasks/digest").status_code == 401

def test_cron_with_secret_ok():
    h = {"X-Cron-Secret": "test-cron"}
    assert c.post("/tasks/refresh-all", headers=h).status_code == 200
    assert c.post("/tasks/digest", headers=h).status_code == 200

def test_bad_shop_rejected():
    assert c.get("/install?shop=evil.com").status_code == 400

def test_billing_subscribe_uses_shopify_hosted_pricing(monkeypatch):
    monkeypatch.setattr(settings, "DEMO", False)
    monkeypatch.setattr(settings, "APP_HANDLE", "restocked-7")
    r = c.get("/billing/subscribe?shop=acme.myshopify.com&plan=growth",
              follow_redirects=False)
    assert r.status_code in (302, 307)
    assert r.headers["location"] == (
        "https://admin.shopify.com/store/acme/charges/"
        "restocked-7/pricing_plans"
    )

def test_billing_callback_accepts_shopify_app_pricing_params(monkeypatch):
    monkeypatch.setattr(settings, "DEMO", False)
    r = c.get("/billing/callback?shop=acme.myshopify.com&plan_handle=growth",
              follow_redirects=False)
    assert r.status_code in (302, 307)
    assert r.headers["location"] == "/?shop=acme.myshopify.com"

def test_billing_callback_accepts_shopify_pricing_shop_domain(monkeypatch):
    monkeypatch.setattr(settings, "DEMO", False)
    r = c.get("/billing/callback?shop_domain=acme.myshopify.com&plan_handle=growth",
              follow_redirects=False)
    assert r.status_code in (302, 307)
    assert r.headers["location"] == "/?shop=acme.myshopify.com"

def test_recommendations_recomputes_legacy_cached_sample(monkeypatch):
    async def fake_compute(shop, token, lead_time_days=None):
        return {
            "recommendations": [],
            "sample": False,
            "sync_status": "orders_unavailable",
            "computed_for": shop,
        }

    monkeypatch.setattr(settings, "DEMO", False)
    monkeypatch.setattr(main, "compute_recommendations", fake_compute)
    app.dependency_overrides[main.require_shop] = lambda: "acme.myshopify.com"
    main.store.update("acme.myshopify.com", token="token", last_run={"sample": True})
    try:
        r = c.get("/api/recommendations")
    finally:
        app.dependency_overrides.pop(main.require_shop, None)
        main.store.delete("acme.myshopify.com")

    assert r.status_code == 200
    assert r.json()["sample"] is False
    assert r.json()["sync_status"] == "orders_unavailable"
