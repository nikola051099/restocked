import asyncio

from app import forecasting


VARIANT_NODES = [
    {
        "id": "gid://shopify/ProductVariant/1",
        "inventoryQuantity": 4,
        "selectedOptions": [
            {"name": "Size", "value": "M"},
            {"name": "Color", "value": "Black"},
        ],
        "product": {"id": "gid://shopify/Product/100", "title": "Tee"},
    }
]


def test_order_sync_failure_does_not_return_sample(monkeypatch):
    class FakeAPI:
        def __init__(self, shop, token):
            pass

        async def fetch_variants(self):
            return VARIANT_NODES

        async def fetch_orders(self, since):
            raise RuntimeError("orders unavailable")

    monkeypatch.setattr(forecasting, "AdminAPI", FakeAPI)
    out = asyncio.run(forecasting.compute_recommendations("acme.myshopify.com", "token"))

    assert out["recommendations"] == []
    assert out["sample"] is False
    assert out["sync_status"] == "orders_unavailable"
    assert out["n_variants"] == 1


def test_empty_order_history_does_not_return_sample(monkeypatch):
    class FakeAPI:
        def __init__(self, shop, token):
            pass

        async def fetch_variants(self):
            return VARIANT_NODES

        async def fetch_orders(self, since):
            return []

    monkeypatch.setattr(forecasting, "AdminAPI", FakeAPI)
    out = asyncio.run(forecasting.compute_recommendations("acme.myshopify.com", "token"))

    assert out["recommendations"] == []
    assert out["sample"] is False
    assert out["sync_status"] == "no_order_history"
    assert out["n_variants"] == 1
