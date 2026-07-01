"""
Seed a Shopify DEVELOPMENT store with realistic apparel data so Restocked has
something to forecast (products with Size/Color variants + a batch of orders).

This is a DEV/TEST tool. It is NOT part of the deployed app and needs WRITE
scopes, which the public Restocked app deliberately does not request. Create a
one-off custom app in your dev store to get a token:

  Shopify admin -> Settings -> Apps and sales channels -> Develop apps
    -> Allow custom app development -> Create an app ("restocked-seed")
    -> Configuration -> Admin API access scopes: check
         write_products, read_products, write_orders, read_orders,
         write_inventory, read_inventory
    -> Save -> Install app -> API credentials -> reveal the
       "Admin API access token" (starts with shpat_...)

Then run (PowerShell):

  $env:SEED_SHOP   = "restocked-test-store.myshopify.com"
  $env:SEED_TOKEN  = "shpat_xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  python scripts/seed_test_store.py            # create products + orders
  python scripts/seed_test_store.py --cleanup  # delete the seeded products

The token is read from your environment and is never stored by this script.
Orders are created with inventory BYPASS so the stock levels set here are what
Restocked reads as "current stock".
"""
from __future__ import annotations

import os
import random
import sys
import time

import httpx

API_VERSION = os.getenv("SEED_API_VERSION", "2026-04")
SHOP = os.getenv("SEED_SHOP", "").strip()
TOKEN = os.getenv("SEED_TOKEN", "").strip()
SEED_TAG = "restocked-seed"

random.seed(7)

# ---- catalog: apparel with real size curves + a sold-out bestseller -------- #

SIZES = ["XS", "S", "M", "L", "XL"]
SIZE_CURVE = {"XS": 0.08, "S": 0.20, "M": 0.32, "L": 0.25, "XL": 0.15}
COLORS = {"Black": 0.60, "Olive": 0.40}

PRODUCTS = [
    {"title": "Everyday Cotton Tee", "type": "T-Shirts", "price": "24.00", "demand": 1.0},
    {"title": "Heavyweight Hoodie", "type": "Hoodies", "price": "58.00", "demand": 0.7},
    {"title": "Merino Beanie", "type": "Accessories", "price": "29.00", "demand": 0.5},
]

# variants that should look understocked (drives "imminent"/"soon" in the app)
LOW_STOCK = {("Everyday Cotton Tee", "M", "Black"): 2,
             ("Heavyweight Hoodie", "L", "Black"): 4,
             ("Everyday Cotton Tee", "S", "Olive"): 3}


def _client() -> httpx.Client:
    return httpx.Client(
        base_url=f"https://{SHOP}/admin/api/{API_VERSION}",
        headers={"X-Shopify-Access-Token": TOKEN,
                 "Content-Type": "application/json"},
        timeout=60,
    )


def gql(client: httpx.Client, query: str, variables: dict | None = None) -> dict:
    for attempt in range(6):
        r = client.post("/graphql.json", json={"query": query,
                                               "variables": variables or {}})
        if r.status_code == 429:
            time.sleep(2 * (attempt + 1))
            continue
        r.raise_for_status()
        body = r.json()
        if "errors" in body:
            throttled = any((e.get("extensions", {}) or {}).get("code") == "THROTTLED"
                            for e in body["errors"])
            if throttled and attempt < 5:
                time.sleep(2 * (attempt + 1))
                continue
            raise SystemExit(f"GraphQL error: {body['errors']}")
        return body["data"]
    raise SystemExit("Throttled after retries")


def _user_errors(payload: dict, key: str) -> None:
    errs = (payload.get(key) or {}).get("userErrors") or []
    if errs:
        raise SystemExit(f"{key} userErrors: {errs}")


def primary_location_id(client: httpx.Client) -> str:
    data = gql(client, "{ locations(first:1){ edges{ node{ id name } } } }")
    edges = data["locations"]["edges"]
    if not edges:
        raise SystemExit("No locations found on this store.")
    print(f"  location: {edges[0]['node']['name']}")
    return edges[0]["node"]["id"]


PRODUCT_SET = """
mutation Seed($input: ProductSetInput!) {
  productSet(synchronous: true, input: $input) {
    product {
      id
      variants(first: 50) {
        edges { node { id inventoryItem { id } selectedOptions { name value } } }
      }
    }
    userErrors { field message }
  }
}"""

INV_SET = """
mutation Inv($input: InventorySetQuantitiesInput!) {
  inventorySetQuantities(input: $input) { userErrors { field message } }
}"""

ORDER_CREATE = """
mutation MakeOrder($order: OrderCreateOrderInput!, $options: OrderCreateOptionsInput) {
  orderCreate(order: $order, options: $options) {
    order { id name }
    userErrors { field message }
  }
}"""

PRODUCT_QUERY = """
query FindSeeded($cursor: String) {
  products(first: 50, after: $cursor, query: "tag:restocked-seed") {
    edges { cursor node { id title } }
    pageInfo { hasNextPage }
  }
}"""

PRODUCT_DELETE = """
mutation Del($input: ProductDeleteInput!) {
  productDelete(input: $input) { deletedProductId userErrors { field message } }
}"""


def build_variants(price: str) -> list[dict]:
    variants = []
    for color in COLORS:
        for size in SIZES:
            variants.append({
                "optionValues": [
                    {"optionName": "Size", "name": size},
                    {"optionName": "Color", "name": color},
                ],
                "price": price,
                "inventoryItem": {"tracked": True},
            })
    return variants


def create_products(client: httpx.Client, location_id: str) -> list[dict]:
    created = []
    for p in PRODUCTS:
        var_input = {
            "title": p["title"],
            "status": "ACTIVE",
            "productType": p["type"],
            "vendor": "Restocked Demo",
            "tags": [SEED_TAG],
            "productOptions": [
                {"name": "Size", "position": 1,
                 "values": [{"name": s} for s in SIZES]},
                {"name": "Color", "position": 2,
                 "values": [{"name": c} for c in COLORS]},
            ],
            "variants": build_variants(p["price"]),
        }
        data = gql(client, PRODUCT_SET, {"input": var_input})
        _user_errors(data, "productSet")
        prod = data["productSet"]["product"]
        variants = []
        for e in prod["variants"]["edges"]:
            node = e["node"]
            opts = {o["name"]: o["value"] for o in node["selectedOptions"]}
            variants.append({
                "variant_id": node["id"],
                "inventory_item_id": node["inventoryItem"]["id"],
                "size": opts.get("Size", ""),
                "color": opts.get("Color", ""),
            })
        print(f"  created '{p['title']}' with {len(variants)} variants")
        created.append({"product": p, "variants": variants})

        # set inventory per variant (weekly demand * ~2 weeks cover, minus low-stock)
        quantities = []
        for v in variants:
            base = weekly_demand(p, v["size"], v["color"])
            stock = LOW_STOCK.get((p["title"], v["size"], v["color"]),
                                  int(round(base * 2)))
            quantities.append({"inventoryItemId": v["inventory_item_id"],
                               "locationId": location_id,
                               "quantity": int(stock)})
            v["stock"] = int(stock)
        inv_input = {"name": "available", "reason": "correction",
                     "ignoreCompareQuantity": True, "quantities": quantities}
        data = gql(client, INV_SET, {"input": inv_input})
        _user_errors(data, "inventorySetQuantities")
    return created


def weekly_demand(product: dict, size: str, color: str) -> float:
    return 12.0 * product["demand"] * SIZE_CURVE[size] * COLORS[color]


def create_orders(client: httpx.Client, created: list[dict], n_orders: int = 40) -> None:
    # build a weighted pool of variants by their demand so popular sizes sell more
    pool = []
    for c in created:
        for v in c["variants"]:
            w = weekly_demand(c["product"], v["size"], v["color"])
            pool.extend([v["variant_id"]] * max(1, int(round(w * 3))))

    made = 0
    for _ in range(n_orders):
        k = random.randint(2, 5)
        picks = random.sample(pool, min(k, len(pool)))
        counts: dict[str, int] = {}
        for vid in picks:
            counts[vid] = counts.get(vid, 0) + random.randint(1, 3)
        line_items = [{"variantId": vid, "quantity": q} for vid, q in counts.items()]
        order = {"lineItems": line_items, "financialStatus": "PAID"}
        options = {"inventoryBehaviour": "BYPASS", "sendReceipt": False,
                   "sendFulfillmentReceipt": False}
        data = gql(client, ORDER_CREATE, {"order": order, "options": options})
        _user_errors(data, "orderCreate")
        made += 1
    print(f"  created {made} orders across seeded variants")


def cleanup(client: httpx.Client) -> None:
    cursor, ids = None, []
    while True:
        data = gql(client, PRODUCT_QUERY, {"cursor": cursor})
        conn = data["products"]
        for e in conn["edges"]:
            ids.append(e["node"]["id"])
            cursor = e["cursor"]
        if not conn["pageInfo"]["hasNextPage"]:
            break
    for pid in ids:
        data = gql(client, PRODUCT_DELETE, {"input": {"id": pid}})
        _user_errors(data, "productDelete")
    print(f"  deleted {len(ids)} seeded products "
          f"(seed orders remain but reference deleted variants, so the app ignores them)")


def main() -> None:
    if not SHOP or not TOKEN:
        raise SystemExit("Set SEED_SHOP and SEED_TOKEN environment variables first "
                         "(see the docstring at the top of this file).")
    if not SHOP.endswith(".myshopify.com"):
        raise SystemExit("SEED_SHOP must be a *.myshopify.com domain.")
    print(f"Store: {SHOP}  (API {API_VERSION})")
    with _client() as client:
        if "--cleanup" in sys.argv:
            print("Cleaning up seeded data...")
            cleanup(client)
            print("Done.")
            return
        loc = primary_location_id(client)
        created = create_products(client, loc)
        create_orders(client, created)
        n_variants = sum(len(c["variants"]) for c in created)
        print(f"\nDone. Seeded {len(created)} products / {n_variants} variants + orders.")
        print("Open Restocked in the admin and click Refresh to see recommendations.")


if __name__ == "__main__":
    main()
