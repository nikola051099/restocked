"""
Shopify Billing API — recurring application charge with a free trial.

Flow: create a charge -> redirect merchant to confirmationUrl -> they approve
-> Shopify redirects back to /billing/callback -> we activate.
"""
from __future__ import annotations

from .config import settings
from .shopify_client import AdminAPI

PLANS = {
    "starter": {"name": "Starter", "price": 19.0, "variant_cap": 1000},
    "growth":  {"name": "Growth",  "price": 39.0, "variant_cap": 5000},
    "pro":     {"name": "Pro",     "price": 79.0, "variant_cap": 100000},
}
TRIAL_DAYS = 14


async def create_subscription(shop: str, token: str, plan_key: str,
                              return_url: str) -> str:
    """Create a recurring charge; return the confirmation URL to redirect to."""
    plan = PLANS[plan_key]
    api = AdminAPI(shop, token)
    mutation = """
    mutation CreateSub($name: String!, $price: Decimal!, $trial: Int!, $url: URL!) {
      appSubscriptionCreate(
        name: $name
        trialDays: $trial
        returnUrl: $url
        lineItems: [{
          plan: { appRecurringPricingDetails: {
            price: { amount: $price, currencyCode: USD }
            interval: EVERY_30_DAYS
          } }
        }]
      ) {
        confirmationUrl
        userErrors { field message }
        appSubscription { id status }
      }
    }"""
    data = await api._gql(mutation, {
        "name": f"{plan['name']} plan",
        "price": plan["price"],
        "trial": TRIAL_DAYS,
        "url": return_url,
    })
    result = data["appSubscriptionCreate"]
    if result["userErrors"]:
        raise RuntimeError(result["userErrors"])
    return result["confirmationUrl"]
