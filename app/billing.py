"""Plan metadata and Shopify App Pricing helpers.

Restocked uses Shopify App Pricing, so Shopify hosts plan selection and handles
charge approval, decline, trials, proration, upgrades, and downgrades.
"""
from __future__ import annotations

from urllib.parse import quote

from .config import settings

PLANS = {
    "starter": {"name": "Starter", "price": 19.0, "variant_cap": 1000},
    "growth":  {"name": "Growth",  "price": 39.0, "variant_cap": 5000},
    "pro":     {"name": "Pro",     "price": 79.0, "variant_cap": 100000},
}
TRIAL_DAYS = 14


def shopify_store_handle(shop: str) -> str:
    """Return the admin store handle from a myshopify.com domain."""
    return shop.split(".", 1)[0]


def pricing_page_url(shop: str) -> str:
    """Return Shopify's hosted plan-selection page for this app and shop."""
    store_handle = quote(shopify_store_handle(shop), safe="")
    app_handle = quote(settings.APP_HANDLE, safe="")
    return f"https://admin.shopify.com/store/{store_handle}/charges/{app_handle}/pricing_plans"
