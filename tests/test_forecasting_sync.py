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


def test_inventory_sync_failure_is_distinct_from_product_sync(monkeypatch):
    product_only_nodes = [
        {k: v for k, v in VARIANT_NODES[0].items() if k != "inventoryQuantity"}
    ]

    class FakeAPI:
        def __init__(self, shop, token):
            pass

        async def fetch_variants(self, page_limit=50, include_inventory=True):
            if include_inventory:
                raise RuntimeError("inventory unavailable")
            return product_only_nodes

    monkeypatch.setattr(forecasting, "AdminAPI", FakeAPI)
    out = asyncio.run(forecasting.compute_recommendations("acme.myshopify.com", "token"))

    assert out["recommendations"] == []
    assert out["sample"] is False
    assert out["sync_status"] == "inventory_unavailable"
    assert out["n_variants"] == 1


def test_product_sync_failure_does_not_return_sample(monkeypatch):
    class FakeAPI:
        def __init__(self, shop, token):
            pass

        async def fetch_variants(self, page_limit=50, include_inventory=True):
            raise RuntimeError("products unavailable")

    monkeypatch.setattr(forecasting, "AdminAPI", FakeAPI)
    out = asyncio.run(forecasting.compute_recommendations("acme.myshopify.com", "token"))

    assert out["recommendations"] == []
    assert out["sample"] is False
    assert out["sync_status"] == "variants_unavailable"
    assert out["n_variants"] == 0
