"""
Glue between Shopify data and the forecasting engine, plus a self-contained
DEMO data generator so the app can run with no Shopify connection.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd

from forecasting_engine import ForecastEngine, ForecastConfig
from .config import settings
from .shopify_client import AdminAPI
from . import data_mapping


def _run(orders_df, variants_df, lead_time_days: int | None) -> dict:
    cfg = ForecastConfig(lead_time_days=lead_time_days or settings.DEFAULT_LEAD_TIME_DAYS)
    recs = ForecastEngine(cfg).recommend(orders_df, variants_df, today=date.today())
    records = json.loads(recs.to_json(orient="records")) if not recs.empty else []
    return {
        "recommendations": records,
        "is_apparel": data_mapping.is_apparel_like(variants_df),
        "n_variants": int(variants_df["variant_id"].nunique()) if not variants_df.empty else 0,
        "n_order_lines": int(len(orders_df)),
        "lead_time_days": cfg.lead_time_days,
        "service_level": cfg.service_level,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


async def compute_recommendations(shop: str, token: str,
                                  lead_time_days: int | None = None) -> dict:
    api = AdminAPI(shop, token)
    since = (date.today() - timedelta(days=550)).isoformat()  # ~18 months
    order_nodes = await api.fetch_orders(since)
    variant_nodes = await api.fetch_variants()
    orders_df = data_mapping.orders_to_df(order_nodes)
    variants_df = data_mapping.variants_to_df(variant_nodes)
    out = _run(orders_df, variants_df, lead_time_days)
    out["computed_for"] = shop
    try:
        out["shop_email"] = await api.fetch_shop_email()
    except Exception:
        out["shop_email"] = ""
    return out


# ---------------------------- DEMO data ----------------------------------- #

def build_demo_payload(lead_time_days: int | None = None) -> dict:
    """Synthetic but realistic hoodie store: 5 sizes x 2 colors, seasonality,
    growth, and a sold-out bestseller (Black/M) to show stockout-aware logic."""
    rng = np.random.default_rng(7)
    sizes = ["XS", "S", "M", "L", "XL"]
    curve = {"XS": 0.08, "S": 0.20, "M": 0.32, "L": 0.25, "XL": 0.15}
    colors = {"Black": 0.62, "Olive": 0.38}
    n_weeks = 70
    today = date.today()
    start = today - timedelta(weeks=n_weeks)

    def seas(m):
        return {1:1.35,2:1.15,3:.95,4:.8,5:.7,6:.6,7:.6,8:.8,9:1.1,10:1.4,11:1.5,12:1.45}[m]

    rows, vrows = [], []
    stockout_vid = "demo-black-m"
    stockout_weeks = set(range(n_weeks - 14, n_weeks - 8))
    for color in colors:
        for size in sizes:
            vid = f"demo-{color}-{size}".lower()
            vrows.append({"variant_id": vid, "product_id": "demo-hoodie",
                          "size": size, "color": color, "current_stock": 0})
    for wi in range(n_weeks):
        wk = start + timedelta(weeks=wi)
        trend = 1.0 + 0.010 * wi
        for color, cw in colors.items():
            for size in sizes:
                vid = f"demo-{color}-{size}".lower()
                mean = 60 * curve[size] * cw * seas(wk.month) * trend
                qty = rng.poisson(max(mean, 0.01))
                if vid == stockout_vid and wi in stockout_weeks:
                    qty = 0
                if qty > 0:
                    rows.append({"order_date": wk, "variant_id": vid, "quantity": int(qty)})

    orders_df = pd.DataFrame(rows)
    variants_df = pd.DataFrame(vrows)
    recent = orders_df[orders_df["order_date"] >= (today - timedelta(weeks=8))]
    avg8 = recent.groupby("variant_id")["quantity"].sum() / 8.0
    variants_df["current_stock"] = variants_df["variant_id"].map(
        lambda v: int(round(float(avg8.get(v, 0.0)) * 2)))
    variants_df.loc[variants_df.variant_id == stockout_vid, "current_stock"] = 3

    out = _run(orders_df, variants_df, lead_time_days)
    # nicer product label for the demo
    for r in out["recommendations"]:
        r["product"] = "Heavyweight Hoodie"
    out["computed_for"] = "demo-store.myshopify.com"
    out["demo"] = True
    return out
