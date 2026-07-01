# Restocked — Project Handoff / Status Doc

A complete brief of what this project is, what was built, where everything lives,
what's done, and what's left. Written so a new person (or AI) can pick it up cold.

_Last updated: 2026-07-01._

---

## 1. What the product is

**Restocked** is a Shopify app that does **size- and color-level (variant-level)
demand forecasting and reorder planning** for apparel / footwear / accessory
brands.

**The problem it solves:** normal inventory tools forecast a *product*, but
apparel sells per variant — you run out of Medium Black while XXL White sits as
dead stock. Restocked forecasts demand for every variant, then tells the merchant
exactly how much of each size/color to reorder and when.

**Why this niche (the validated wedge):**
- Shopify is **deprecating Stocky** (its old inventory app), leaving merchants
  hunting for a replacement.
- Apparel merchants have a real, repeated pain (size-level stockouts) and pay for
  solutions; existing competitors are weak on variant-level forecasting.
- We validated this via competitor review mining + research before building.

**Pricing:** Starter $19/mo, Growth $39/mo, Pro $79/mo. 14-day free trial. Monthly.

---

## 2. Key accounts, IDs, and links

| Thing | Value |
|---|---|
| Shopify Partner org | **EasyLife** (org id `5014717`) |
| Partner account | Nikola Dordevic — nikola050304@gmail.com |
| App name (Partner) | Restocked |
| App Store listing name | Restocked: Size Forecasting |
| App ID | `390335135745` |
| Client ID / API key | `20cd42154163ff5f21ff163f882dcc01` |
| Dev Dashboard org | `224337351` |
| GitHub repo | https://github.com/nikola051099/restocked (branch `main`) |
| Live app URL | https://restocked.onrender.com |
| Privacy policy | https://restocked.onrender.com/privacy |
| Terms | https://restocked.onrender.com/terms |
| Dev / test store | restocked-test-store.myshopify.com |
| Render web service | `srv-d906o668bjmc738uvvlg` ("restocked", Starter plan) |
| Render extras | restocked-db (Postgres), restocked-refresh + restocked-digest (crons) |
| Screencast (unlisted) | https://youtu.be/7FpYbhMDwXA |
| Local project folder | C:\Users\Kosmaj\Claude\Projects\Business |

Key dashboards:
- App Store submission checklist: https://partners.shopify.com/5014717/apps/390335135745/distribution/app-store
- Listing editor: https://apps.shopify.com/services/partner-app-submissions/20cd42154163ff5f21ff163f882dcc01/en
- API access / protected data: https://partners.shopify.com/5014717/apps/390335135745/api_access
- Pricing plans: https://apps.shopify.com/services/pricing/20cd42154163ff5f21ff163f882dcc01
- Render: https://dashboard.render.com/web/srv-d906o668bjmc738uvvlg

**Secrets** (NOT in this doc): SHOPIFY_API_SECRET, APP_SECRET, CRON_SECRET, DATABASE_URL,
SMTP creds — all live as **environment variables in the Render service**, and the
API secret in the **Dev Dashboard**. Never commit these.

---

## 3. Tech stack & architecture

Python **FastAPI** app, Jinja2 templates, pandas/numpy, SQLAlchemy (Postgres),
httpx. Deployed on Render from GitHub. Embedded Shopify admin app (App Bridge +
session-token auth).

### Repo layout (C:\Users\Kosmaj\Claude\Projects\Business)
- **forecasting_engine/engine.py** — core IP. `ForecastEngine.recommend(orders_df, variants_df, today)`,
  `ForecastConfig(lead_time_days=30, review_period_days=14, service_level=0.95)`.
  Stockout-aware level estimation, deseasonalized trend, safety stock
  (z * std * sqrt(weeks)), reorder points, size-curve share, sparse/Croston-style handling.
- **forecasting_engine/test_engine.py** — synthetic apparel test.
- **app/main.py** — FastAPI entry. Routes: `/healthz`, `/install`, `/auth/callback`,
  `/` (dashboard), `/api/recommendations`, `/api/refresh`, `/tasks/refresh-all`,
  `/tasks/digest`, `/billing/subscribe`, `/billing/callback`. Sets CSP
  `frame-ancestors` for Shopify admin.
- **app/shopify_client.py** — OAuth + Admin GraphQL API (retry/backoff on 429/THROTTLED):
  `fetch_orders`, `fetch_variants`, `fetch_shop_email`, `verify_hmac`, `verify_webhook`,
  `exchange_code_for_token`.
- **app/auth.py** — `verify_session_token` (manual HS256 JWT), `require_shop` dependency.
- **app/data_mapping.py** — `orders_to_df`, `variants_to_df` (size/color from
  selectedOptions), `is_apparel_like`.
- **app/forecasting.py** — `compute_recommendations` (pulls ~550 days of orders,
  syncs variants first, runs the engine, and returns accurate empty sync states
  when Shopify products/orders are unavailable or the store has no order history),
  `build_demo_payload` (synthetic hoodie data for local/demo mode only).
- **app/config.py** — env-var settings.
- **app/store.py** — `Store` (Postgres via SQLAlchemy, or in-memory fallback).
- **app/billing.py** — PLANS (starter $19 / growth $39 / pro $79), TRIAL_DAYS=14,
  and Shopify App Pricing helpers that redirect merchants to Shopify's hosted
  plan-selection page.
- **app/webhooks.py** — mandatory GDPR webhooks: `/webhooks/app/uninstalled`,
  `/customers/data_request`, `/customers/redact`, `/shop/redact` (HMAC-verified).
- **app/legal.py** — `/privacy` and `/terms` pages.
- **app/templates/dashboard.html** — embedded dashboard (Polaris-style): metric cards,
  ranked reorder table, urgency filters, search, sortable columns, color swatches,
  adjustable lead time, "show your math" expandable rows, CSV export, App Bridge +
  session-token fetch.
- **render.yaml** — blueprint: web + Postgres + 2 cron jobs, `PYTHON_VERSION=3.11.9`.
- **shopify.app.toml** — CLI config: client_id, scopes (read_orders, read_products,
  read_inventory), redirect_urls, GDPR compliance webhooks.
- **jobs/refresh_all.py**, **jobs/send_digests.py** — cron entry scripts.
- **tests/** — pytest suite (auth, api, digest).
- **assets/icon.* , assets/screenshots/** — app icon + 3 listing screenshots (1600x900).
- Docs: MVP-spec, lean-build-roadmap, PUBLISH-CHECKLIST, listing-copy, DEPLOY, etc.

### How auth works (important)
- Install: `/install` -> Shopify OAuth -> `/auth/callback` (HMAC + state verified) ->
  token exchange -> token stored.
- Embedded data calls: dashboard JS calls `shopify.idToken()` (App Bridge) and sends
  `Authorization: Bearer <jwt>`; backend verifies the HS256 JWT in `app/auth.py`.
- App Bridge script loads from `https://cdn.shopify.com/shopifycloud/app-bridge.js`;
  page has `<meta name="shopify-api-key">`.

### Production sync states (why live review no longer shows samples)
`read_orders` can return **403 until protected customer data access is approved**
(approved during App Store review). The production app now reports that accurately:
it syncs variants first, then shows an empty "Order history unavailable" or "No
order history yet" state instead of synthetic recommendations. This fixes Shopify
review requirement 2.1.4 ("Synchronize data accurately").

Synthetic hoodie data still exists, but only through `DEMO=1` local/demo mode.
Production also ignores any old cached `sample: true` payloads and recomputes, so
reviewers do not see stale sample data after deploy.

Default `read_orders` returns only recent orders; the optional `read_all_orders`
scope — NOT yet requested — would give the full ~18 months the engine can use for
seasonality.

---

## 4. Deploy process (how to ship changes)

1. Edit code locally in C:\Users\Kosmaj\Claude\Projects\Business.
2. Commit + push from **PowerShell** (run from the repo folder):
   ```
   cd "C:\Users\Kosmaj\Claude\Projects\Business"
   git add -A
   git commit -m "message"
   git push
   ```
   - If you see a `.git/index.lock` or `HEAD.lock` error: `Remove-Item .git\index.lock,.git\HEAD.lock -Force` then retry.
3. **Render does NOT auto-deploy.** Go to the Render service ->
   **Manual Deploy -> Deploy latest commit**. Wait ~2-4 min for "Live".
4. The in-memory cache resets on deploy; the dashboard may show old cached data until
   you click **Refresh forecast** in the app.

---

## 5. What is DONE

- App fully built, deployed, and **verified working end-to-end** inside the embedded
  Shopify admin (dashboard loads via session-token auth, all features work).
- Accurate empty sync states for stores where products/orders are unavailable or
  order history is empty; demo/sample data is limited to `DEMO=1`.
- **App Store listing 100% complete, 0 issues**: name, category (Orders & shipping ->
  Inventory -> Inventory optimization) + detail tags, English language, app intro,
  500-char description, 5 features, app-card subtitle, 5 search terms, feature media +
  3 desktop screenshots (with alt text), support + contact emails (nikola050304@gmail.com),
  privacy URL, sales-channel = "doesn't require", test account = "no account required",
  testing instructions, **screencast URL** (the YouTube link). Testing instructions
  were updated 2026-07-01 to remove stale "demo dataset" language and explain
  Shopify App Pricing plus accurate empty sync states.
- **3 pricing plans** created with display names + feature bullets (Starter/Growth/Pro,
  14-day trial each).
- **Shopify App Pricing enabled** in Partner Dashboard pricing settings on
  2026-07-01. It was previously still set to Manual pricing, which likely caused
  the billing review failure. Default billing frequency is now Monthly. Pricing
  index shows public starter/growth/pro plans with monthly prices and 14-day trials.
- **Plan redirect URLs fixed** on 2026-07-01: public starter/growth/pro and the
  private `shopify-test` plan now redirect to `/billing/callback` after plan
  selection. The private `$0/month` `shopify-test` plan has
  `restocked-test-store.myshopify.com` in its store access list.
- **Protected customer data request** filled and saved (data use = "Store management",
  NO optional PII fields requested, all **9/9** data-protection questions answered).
  Status = Draft; it's reviewed automatically when the app is submitted.
- **Emergency contact** (phone) added in Partner settings.
- **App capabilities** = Embedded.
- **Automated checks for common errors = PASSED (green)**: authenticates after install,
  redirects to UI, mandatory compliance webhooks, HMAC verification, valid TLS.
- Payout: a **EUR bank account** is connected in Partner settings. (Canada tax section
  is irrelevant for a Serbia-based partner — skip it.)

---

## 6. What is LEFT (Shopify review resubmission)

Shopify paused review on 2026-07-01 for:
- **1.2.2 Billing**: reviewer hit an internal server error when choosing a plan.
- **2.1.4 Sync accuracy**: reviewer saw data that did not accurately reflect the
  Shopify store state.
- **4.5.4 / 4.5.5 Testing instructions**: make sure review credentials/instructions
  are complete.

Code fixes made:
- `/billing/subscribe` no longer calls the old Billing API. It redirects to
  Shopify App Pricing:
  `https://admin.shopify.com/store/:store_handle/charges/:app_handle/pricing_plans`.
- The dashboard plan link uses `target="_top"` so the Shopify-hosted pricing page
  opens correctly from the embedded app.
- `/billing/callback` accepts Shopify App Pricing params (`plan_handle`,
  `shop_domain`, `myshopify_domain`) and never 500s on approve/decline callbacks.
- Production recommendations no longer show synthetic sample data. Product/order
  sync failures return accurate empty states, and stale cached sample payloads are
  ignored.

Current status after 2026-07-01 checks:
1. **Render/live app:** deployed and returning the correct App Bridge root page.
   `/billing/subscribe?shop=restocked-test-store.myshopify.com&plan=growth`
   redirects to Shopify's hosted pricing URL with handle
   `restocked-size-forecasting`.
2. **Render env:** `SHOPIFY_APP_HANDLE=restocked-size-forecasting` confirmed as
   required; live redirect currently uses that handle.
3. **Partner Dashboard -> Pricing:** switched from Manual pricing to Shopify App
   Pricing and saved. Default billing frequency set to Monthly. Pricing index
   shows 3 public plans: starter/growth/pro with monthly prices and 14-day trials.
   All public plan redirect URLs are `/billing/callback`.
4. **Partner Dashboard -> Private test plan:** `shopify-test` is a `$0/month`
   private test plan, redirects to `/billing/callback`, and authorizes
   `restocked-test-store.myshopify.com`.
5. **Partner Dashboard -> Testing instructions:** updated and saved. They now say
   no separate Restocked account is required, first-open plan selection uses
   Shopify App Pricing, and unavailable order history displays an accurate empty
   sync state instead of fake recommendations.

Still required before resubmitting:
1. **Fresh install pricing test:** the existing dev-store install still returns to
   the installed apps page when opening the hosted pricing URL, even after Shopify
   App Pricing, plan redirect URLs, and private test-plan store access were fixed.
   Because this app was installed before Shopify App Pricing was enabled, test
   from a fresh install (uninstall/reinstall on
   `restocked-test-store.myshopify.com` or use a fresh dev store) and confirm the
   plan selector appears.
2. **Resubmit fixes** from the Partner Dashboard review page after the fresh-install
   pricing test is satisfactory.

Optional / later:
- Request the **`read_all_orders`** scope (API access page) for full ~18-month order
  history -> better seasonality. Not required to launch.

---

## 7. After approval (to actually earn)

- **Revenue share: Shopify takes 0%** until $1M USD lifetime earned (then 15%). So you
  keep ~100% of subscription revenue now.
- Per paying merchant ≈ the plan price converted USD->EUR minus a small (~0.5%)
  conversion fee: Starter ≈ €17, Growth ≈ €35, Pro ≈ €71 per month.
- Total income = (paying merchants) × plan. **The hard part is getting installs**, not
  building. Expect ~0 at first; grows with reviews + marketing.
- **Marketing for installs:** ride the Stocky-shutdown angle (r/shopify, Shopify
  community, DTC/apparel groups); direct outreach to apparel brands; push first users
  to leave App Store reviews (ranking flywheel); agencies/3PLs; later App Store ads.
- Make sure Partner **payout details** are complete so money can actually land.

---

## 8. Gotchas / lessons learned (read before editing)

- **The file editor silently TRUNCATED large files on save** (hit dashboard.html and
  forecasting.py — cut off mid-function, which broke the live app). ALWAYS verify the
  end of any file after editing (e.g. `tail` it) and confirm closing tags / final
  statements are intact. Safer to write large changes via a script and re-read.
- **git in any sandbox can't push** (no credentials) and leaves `.git/*.lock` files —
  push from PowerShell, delete lock files if needed.
- **Render has no auto-deploy** — always Manual Deploy -> Deploy latest commit.
- **PYTHON_VERSION pinned to 3.11.9** (newer Python tried to compile pandas from source
  and failed).
- **Orders API 403** until protected-customer-data is approved is expected. The
  production app must show an accurate empty sync state, not fake sample data.
- **Lead-time apply** had a URL bug (used `&lead_time=` producing a 404); fixed to
  `?lead_time=`. Watch the `api()` URL helper if you add params.

---

## 9. One-line status

Shopify review is paused for billing and sync-accuracy fixes. Code fixes are live,
Shopify App Pricing is enabled in Partner Dashboard, and testing instructions are
updated. Remaining check: verify the hosted pricing selector from a fresh install,
then click **Submit fixes** in Partner Dashboard.
