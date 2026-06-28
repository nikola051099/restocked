# Your Next Steps — what only you can do

The code is built, tested, and ready. I can't create accounts, enter secrets,
take payment, deploy under your name, or submit to Shopify — those are yours.
Here's the exact path, in order. Realistic time to live + reviewed: ~1–2 weeks.

## Step 1 — Shopify Partner account (free, ~15 min)
1. Sign up at partners.shopify.com.
2. Create a development store (Stores → Add store → Development store).
3. Apps → Create app → Create app manually. Name it Restocked.
4. Copy the API key and API secret key. You'll need them for the env vars.

## Step 2 — Add test data to your dev store (~15 min)
Add 5–10 products that have Size and Color variants, and place a handful of test
orders across different sizes (so the engine has history to forecast).

## Step 3 — Run it locally once (~30 min)
Follow DEPLOY.md "Run locally". Confirm the dashboard loads in demo mode, then
install on your dev store with your real API key/secret and confirm real
recommendations appear. This is where theory meets your real data.

## Step 4 — Deploy (~1–2 hrs)
Follow DEPLOY.md steps 1–7. End state: a public URL, a database, nightly jobs,
and the app installed on your dev store from the live URL.

## Step 5 — Billing & listing
1. Decide final prices (defaults: $19 / $39 / $79, 14-day trial). These are set
   in the Partner dashboard / via the Billing API already wired in `app/billing.py`.
2. Pay the one-time $19 App Store listing fee.
3. Fill the listing using `listing-copy.md`. Capture the 4 screenshots listed there.
4. Provide a privacy policy URL and support email (required).

## Step 6 — Submit for review (then wait 3–10 business days)
Shopify runs automated checks first (OAuth, embedded session tokens, GDPR
webhooks — all implemented). Expect 1–2 rounds of small fixes. Resubmit and pass.

## Step 7 — First installs (the real growth work)
- Publish the landing page (`landing.html`) on Netlify/Vercel/GitHub Pages and
  wire the form to a service like Formspree (replace the form action). Collect emails.
- Offer the app free to 5–10 apparel brands for honest feedback + a review.
- First reviews break the cold-start ranking — prioritize them.

## Things I deliberately left for you (and why)
- Accounts, API keys, payments, OAuth approval, app submission — require your identity.
- SMTP credentials for the digest — your email provider account.
- The first customer conversations — the one validation no code can replace.

## What's already done (so you don't redo it)
- Forecasting engine (size-level, stockout-aware, seasonal) — tested.
- Full Shopify app: OAuth, embedded dashboard, Admin API pull, billing, GDPR webhooks.
- Session-token auth + CSP (the two most common review rejections) — handled.
- Adjustable lead time, CSV export, search/filter/sort, weekly email digest.
- Deploy config (render.yaml, Procfile), nightly jobs, automated test suite (16 tests).
- Listing copy, landing page, this guide.
