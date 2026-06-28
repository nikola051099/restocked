# Variant Forecasting App (Shopify)

Size/color-level demand forecasting + reorder recommendations for apparel stores.
Built around `forecasting_engine/` (the model) wrapped in a FastAPI Shopify app.

> Not yet published. See `PUBLISH-CHECKLIST.md` for the full path to live + the
> honest timeline (deploy + Shopify review = ~2 weeks before first install).

## Layout
```
forecasting_engine/   # the model (tested) — engine.py, test_engine.py
app/
  main.py             # FastAPI: OAuth, dashboard, recommendations API, billing
  shopify_client.py   # OAuth handshake + Admin GraphQL (orders, variants)
  data_mapping.py     # Shopify response -> engine input DataFrames
  forecasting.py      # glue: pull data, run engine
  billing.py          # Shopify recurring charge ($19/$39/$79 + 14-day trial)
  webhooks.py         # mandatory GDPR + app/uninstalled webhooks
  store.py            # token/settings storage (Postgres or in-memory)
  templates/dashboard.html  # embedded UI with "show your math"
```

## Run locally
1. `pip install -r requirements.txt`
2. `cp .env.example .env` and fill `SHOPIFY_API_KEY` / `SHOPIFY_API_SECRET`
   (from your Shopify Partner app) and `APP_SECRET` (any long random string).
3. `uvicorn app.main:app --reload`
4. Expose it: `ngrok http 8000` (or cloudflared). Put the https URL in `.env`
   as `APP_URL`, and in the Partner dashboard as the App URL and
   `…/auth/callback` as the redirect URL.
5. Install on your dev store: open
   `https://YOUR_TUNNEL/install?shop=yourstore.myshopify.com`

## Deploy (prod)
- Push to GitHub, connect to Render/Railway/Fly.io.
- Add Postgres; set `DATABASE_URL` + the env vars from `.env`.
- Set `APP_URL` to the prod URL; update the Partner dashboard URLs to match.
- Nightly forecast: hit `/api/recommendations?shop=…` per active shop on a cron
  (Render Cron Job / GitHub Actions), or add APScheduler.

## Tests
- `cd forecasting_engine && python test_engine.py` — engine sanity checks.
- `python test_data_mapping.py` — confirms Shopify payloads feed the engine.

## Notes
- Scopes requested: `read_orders, read_products, read_inventory`.
- We store no customer PII — only aggregated per-variant demand — which keeps
  the GDPR webhooks trivial and reduces your compliance surface.
- Engine refinements to do against real data are listed in `lean-build-roadmap.md`.
