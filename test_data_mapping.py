"""
Verifies the Shopify->engine data mapping end to end, using a small fake
Admin API payload (same shape the GraphQL queries return). Confirms the
mapped DataFrames feed the engine and produce recommendations.
"""
from datetime import date, timedelta
from app import data_mapping
from forecasting_engine import ForecastEngine, ForecastConfig


def fake_order_nodes():
    today = date.today()
    nodes = []
    # 30 weeks of weekly orders for two variants
    for w in range(30):
        d = (today - timedelta(weeks=30 - w)).isoformat()
        nodes.append({
            "createdAt": d,
            "lineItems": {"edges": [
                {"node": {"quantity": 5 + w % 3,
                          "variant": {"id": "gid://shopify/ProductVariant/1"},
                          "product": {"id": "gid://shopify/Product/100"}}},
                {"node": {"quantity": 2,
                          "variant": {"id": "gid://shopify/ProductVariant/2"},
                          "product": {"id": "gid://shopify/Product/100"}}},
            ]},
        })
    return nodes


def fake_variant_nodes():
    return [
        {"id": "gid://shopify/ProductVariant/1", "inventoryQuantity": 4,
         "selectedOptions": [{"name": "Size", "value": "M"},
                             {"name": "Color", "value": "Black"}],
         "product": {"id": "gid://shopify/Product/100", "title": "Tee"}},
        {"id": "gid://shopify/ProductVariant/2", "inventoryQuantity": 30,
         "selectedOptions": [{"name": "Size", "value": "XS"},
                             {"name": "Colour", "value": "Black"}],
         "product": {"id": "gid://shopify/Product/100", "title": "Tee"}},
    ]


def main():
    orders_df = data_mapping.orders_to_df(fake_order_nodes())
    variants_df = data_mapping.variants_to_df(fake_variant_nodes())

    assert list(orders_df.columns) == ["order_date", "variant_id", "quantity"]
    assert set(["variant_id", "product_id", "size", "color", "current_stock"]) \
        <= set(variants_df.columns)
    # option-name aliasing worked ("Colour" -> color)
    assert variants_df.loc[variants_df.variant_id.str.endswith("/2"), "color"].iloc[0] == "Black"
    assert data_mapping.is_apparel_like(variants_df) is True
    print("[ok] mapping produced engine-ready DataFrames")
    print(f"     {len(orders_df)} order lines, {len(variants_df)} variants")

    engine = ForecastEngine(ForecastConfig(lead_time_days=30))
    recs = engine.recommend(orders_df, variants_df, today=date.today())
    assert not recs.empty
    # the low-stock M should be more urgent than the overstocked XS
    m = recs[recs["size"] == "M"].iloc[0]
    xs = recs[recs["size"] == "XS"].iloc[0]
    assert m["recommended_order_qty"] >= xs["recommended_order_qty"]
    print("[ok] engine ran on mapped data; low-stock M flagged for more reorder than XS")
    print(recs[["size", "color", "current_stock", "days_of_cover_left",
                "stockout_risk", "recommended_order_qty"]].to_string(index=False))
    print("\nData mapping + engine integration works.")


if __name__ == "__main__":
    main()
