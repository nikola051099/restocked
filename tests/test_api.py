from fastapi.testclient import TestClient
from app.config import settings
from app.main import app

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
