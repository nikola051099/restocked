# Lean Build Roadmap — Variant Forecasting App

*Strategy: build the minimum shippable app, list it on the Shopify App Store, and let installs + reviews be the validation. The forecasting engine (the hard part and your moat) is already built and tested.*

---

## What's already done

`forecasting_engine/engine.py` — variant-level forecasting + reorder engine. Tested in `test_engine.py`; all sanity checks pass, including the critical stockout case (a sold-out bestseller is still forecast correctly and flagged urgent). This is your IP. Everything below is plumbing around it.

---

## Architecture (keep it boring)

```
Shopify store
   │  (OAuth install, webhooks, Admin API)
   ▼
App backend  ──►  Postgres (orders, variants, recommendations)
   │                  ▲
   │                  │  nightly job
   ▼                  │
Forecast service  ────┘   ← your engine.py runs here
(Python: FastAPI)
   ▲
   │  embedded admin UI (Shopify App Bridge + Polaris)
   ▼
Merchant sees: dashboard of reorder recommendations + "show your math"
```

Two services, one job:
1. **App backend** — handles Shopify OAuth, pulls order history via Admin API (GraphQL `orders`/`lineItems`), stores it, serves the embedded UI.
2. **Forecast service** — runs `engine.py` nightly per store, writes recommendations to the DB.

For a lean v1 you can collapse both into a single Python (FastAPI) app; split later only if you need to.

---

## Recommended stack (play to your strengths)

| Layer | Choice | Why |
|---|---|---|
| Forecast engine | **Python** (done) | Your strength; the moat; already built |
| Backend + API | **Python + FastAPI** | One language end-to-end; fast to ship |
| Shopify OAuth/webhooks | `shopify-python-api` or raw OAuth | Well-documented |
| DB | **Postgres** (Supabase/Neon free tier) | Free to start, scales |
| Embedded UI | **Shopify App Bridge + Polaris React** | Required look-and-feel; passes review faster |
| Hosting | **Render / Railway / Fly.io** | Cheap, simple, background-job support |
| Scheduler | Render cron / APScheduler | Nightly forecast run |

(Shopify's official templates are Node/Remix. You *can* go that route, but a Python backend lets you reuse the engine directly instead of porting it. Recommended: Python.)

---

## Build order (each step ships something testable)

**Step 1 — Partner account + skeleton app (week 1).**
Create a Shopify Partner account (free) and a dev store. Scaffold OAuth so the app installs on your dev store and reads orders. Milestone: "app installs and can fetch my dev store's order history."

**Step 2 — Wire real data into the engine (week 1–2).**
Map Admin API order line items → the engine's `orders_df` / `variants_df` shape (already defined in `engine.py` docstring). Pull `current_stock` from inventory levels, lead time from a per-supplier setting (default 30 days for v1). Milestone: "engine produces recommendations from real Shopify data."

**Step 3 — The one screen that matters (week 2–3).**
A single dashboard: a sortable table of reorder recommendations (urgency, size, current stock, days of cover, recommended qty) with an expandable "show your math" row per variant. That trust panel is the feature — don't skimp on it. Milestone: "merchant sees actionable, explained recommendations."

**Step 4 — Weekly email digest (week 3).**
"Here's what to reorder this week," grouped by urgency. This is the retention hook. Milestone: "app emails a useful digest on a schedule."

**Step 5 — Billing + listing (week 3–4).**
Add Shopify Billing API (recurring charge, $19/$39/$79 tiers). Write the listing: title with keywords ("size-level inventory forecasting for apparel"), screenshots, the bestseller-stockout story as your hero example. Pay the $19 one-time listing fee. Submit for review. Milestone: "live on the App Store."

**Step 6 — First installs & reviews (week 4+).**
This is where the App Store validates. Get your first installs (your landing-page waitlist, apparel communities, free-for-feedback offers). First reviews break the cold-start ranking. Iterate on whatever the first 5 merchants hit.

---

## Deliberately NOT in v1 (from the MVP spec)

Purchase-order management, multi-location balancing, bundles/BOM, 3PL/WMS integrations, landed cost, a reports builder. Each one multiplies your support load. Ship the forecast + the digest. That's it.

---

## Engine refinements to do once real data is flowing (honest list)

The engine is solid but v1, not perfect. Tune these against real stores, not synthetic data:

1. **Trend vs. seasonality interaction.** A trend fit over a window that spans a seasonal decline can read demand as "falling" when it's just off-season. Consider deseasonalising before fitting the trend.
2. **Safety stock on stockout-inflated variance.** Zero-weeks from stockouts inflate the std and over-pad safety stock. Compute variance on in-stock weeks only.
3. **Lead-time/MOQ/case-pack constraints.** Real reorders round to supplier case packs and minimums — add per-supplier constraints.
4. **Cold-start variants** (brand-new products with no history) — borrow the parent style's size curve until they have their own data.

None block launch; they're how you get from "good" to "merchants trust it."

---

## Rough running costs (so there are no surprises)

- Shopify listing fee: **$19 one-time**.
- Hosting + DB: **$0–25/mo** on free/hobby tiers until you have paying users.
- Domain (for landing page): **~$12/yr**.

Effectively zero-investment to launch, as planned. The cost is your time.

---

## How "the App Store validates" actually reads

- **Green:** installs trickle in from the listing without you pushing hard, trial→paid conversion is non-zero, early reviews mention the forecasting being *accurate/useful*. Build more.
- **Yellow:** installs but no conversions → pricing or the value isn't landing; talk to the installers.
- **Red:** you can't get installs even with the listing live and some outreach → demand isn't there at the price; revisit the bundle/BOM wedge with the engine you've already built (it adapts).
