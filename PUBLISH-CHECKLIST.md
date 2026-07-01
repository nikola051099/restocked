# Publish Checklist — Variant Forecasting App

Every step to go from code to a live, paid Shopify app. Marked **[YOU]** (only you can do it — login, credentials, payment, consent) or **[DONE]** (I've built it / can build it).

**Realistic timeline:** ~1–2 days of your hands-on work to deploy + submit, then **3–10 business days of Shopify review**, then the cold-start period before first revenue. Not today. Plan for first install in ~2 weeks and first dollar in the weeks after.

---

## Phase 0 — Code (mostly done today)
- [DONE] Forecasting engine, tested (`forecasting_engine/`).
- [DONE] FastAPI app: OAuth, Admin API pull, engine integration, dashboard, billing (`app/`).
- [DONE] `README.md` with run/deploy instructions, `.env.example`, `requirements.txt`.
- [YOU] Read the README, run it locally once against a dev store (Phase 2).

## Phase 1 — Accounts (you, ~30 min)
- [YOU] Create a **Shopify Partner account** — partners.shopify.com (free).
- [YOU] Create a **development store** from the Partner dashboard (free sandbox).
- [YOU] In Partners → Apps → Create app → get **API key** and **API secret**.
- [YOU] Add a few test products *with size/color variants* and some fake orders to the dev store (so the engine has data).

## Phase 2 — Run locally (you, ~1–2 hrs)
- [YOU] Copy `.env.example` → `.env`, paste your API key/secret.
- [YOU] `pip install -r requirements.txt`, then `uvicorn app.main:app --reload`.
- [YOU] Use a tunnel (ngrok/cloudflared) so Shopify can reach your local app; set the tunnel URL as the app URL + redirect URL in the Partner dashboard.
- [YOU] Install the app on your dev store; confirm the dashboard shows recommendations from your test orders.

## Phase 3 — Deploy (you, ~1–2 hrs)
- [YOU] Create a **Render/Railway/Fly.io** account; connect this repo.
- [YOU] Add a managed **Postgres** (Render/Neon/Supabase free tier).
- [YOU] Set env vars (API key/secret, DB URL, app URL) in the host.
- [YOU] Deploy; set the production URL as the app URL + redirect URL in Partners.
- [YOU] Add the nightly forecast cron (instructions in README).

## Phase 4 — Billing (you confirm, [DONE] code)
- [DONE] Shopify App Pricing redirect code (`app/billing.py`) for the hosted
  plan-selection page.
- [YOU] Decide final prices (suggested $19 / $39 / $79). Set a free trial (14 days).
- [YOU] In Partner Dashboard pricing, set each plan's welcome/redirect link to
  `/billing/callback` or `https://<your-app>/billing/callback`.
- [YOU] Test the hosted plan-selection flow on the dev store.

## Phase 5 — Listing (you write, I can draft)
- [YOU] In Partners → Distribution → choose **Shopify App Store** listing.
- [DONE/me] I can draft the listing copy: title, tagline, description, keywords.
- [YOU] Create screenshots (the dashboard + the "show your math" panel + the bestseller-stockout example as the hero).
- [YOU] Provide privacy policy URL + support email (required).
- [YOU] Pay the **$19 one-time** App Store fee.

## Phase 6 — Submit for review (you, then wait)
- [YOU] Run through Shopify's automated checks (they list requirements; the app must use OAuth correctly, handle GDPR webhooks, be embedded with App Bridge).
- [DONE] Mandatory GDPR/compliance webhook handlers (`app/webhooks.py`).
- [YOU] Submit. **Wait 3–10 business days** for review; expect 1–2 rounds of fixes.

## Phase 7 — Go live + first installs (the real work)
- [YOU] Publish once approved.
- [YOU] Drive first installs: your landing-page waitlist, apparel/Shopify communities, free-for-feedback offers to 5–10 apparel brands.
- [YOU] First reviews break cold-start ranking — prioritize them.
- [me] I can help with launch posts, onboarding emails, and iterating from feedback.

---

## What "earning money" actually requires (honest chain)
live app → installs → trial starts → trial→paid conversions → MRR. Each arrow takes time. The fastest realistic first paid customer is **weeks** away, not hours. That's not failure — it's how every SaaS works.
