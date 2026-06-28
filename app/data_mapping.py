"""
Map raw Shopify Admin API responses into the DataFrames the engine expects.

engine input contract (see forecasting_engine/engine.py):
  orders_df:   order_date, variant_id, quantity
  variants_df: variant_id, product_id, size, color, current_stock [, in_stock_weeks]
"""
from __future__ import annotations

import pandas as pd

_SIZE_KEYS = {"size", "sizes", "größe", "taille", "talla", "size (us)"}
_COLOR_KEYS = {"color", "colour", "colors", "farbe", "couleur", "color/pattern"}


def orders_to_df(order_nodes: list[dict]) -> pd.DataFrame:
    rows = []
    for o in order_nodes:
        created = o.get("createdAt")
        for edge in o.get("lineItems", {}).get("edges", []):
            li = edge["node"]
            variant = li.get("variant") or {}
            vid = variant.get("id")
            qty = li.get("quantity", 0)
            if vid and qty:
                rows.append({"order_date": created, "variant_id": vid,
                             "quantity": int(qty)})
    df = pd.DataFrame(rows, columns=["order_date", "variant_id", "quantity"])
    if not df.empty:
        df["order_date"] = pd.to_datetime(df["order_date"])
    return df


def _extract_option(options: list[dict], keys: set[str]) -> str:
    for opt in options:
        if (opt.get("name") or "").strip().lower() in keys:
            return (opt.get("value") or "").strip()
    return ""


def variants_to_df(variant_nodes: list[dict]) -> pd.DataFrame:
    rows = []
    for v in variant_nodes:
        opts = v.get("selectedOptions", []) or []
        rows.append({
            "variant_id": v.get("id"),
            "product_id": (v.get("product") or {}).get("id", ""),
            "size": _extract_option(opts, _SIZE_KEYS),
            "color": _extract_option(opts, _COLOR_KEYS),
            "current_stock": int(v.get("inventoryQuantity") or 0),
        })
    return pd.DataFrame(
        rows,
        columns=["variant_id", "product_id", "size", "color", "current_stock"],
    )


def is_apparel_like(variants_df: pd.DataFrame, min_share: float = 0.4) -> bool:
    if variants_df.empty:
        return False
    has_size = (variants_df["size"].astype(str).str.len() > 0).mean()
    return bool(has_size >= min_share)
