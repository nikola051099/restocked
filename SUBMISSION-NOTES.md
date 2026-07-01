# Restocked — App Store resubmission notes

Copy these into the Partner Dashboard when you resubmit.

## Testing instructions (requirements 4.5.4 / 4.5.5)

> No separate app account or login credentials are required. Install and open
> Restocked directly from the Shopify admin — authentication uses the embedded
> App Bridge session token automatically, so the reviewer has full access to the
> complete feature set just by opening the app.
>
> Billing uses Shopify Managed Pricing. In the app, click "Manage plan" (top
> right) to open Shopify's hosted plan-selection page, where a charge can be
> accepted, declined, and re-requested on reinstall. Plans: Starter $19/mo,
> Growth $39/mo, Pro $79/mo, each with a 14-day free trial.
>
> Restocked forecasts reorder quantities per variant from the store's own order
> history. On a store with sales history, the dashboard lists variant-level
> recommendations with stockout risk and an expandable "show your math" panel.
> If the store has no orders yet, or protected order access has not been granted,
> the app shows an accurate empty state ("No order history yet") — it never shows
> placeholder or sample data as if it were the merchant's real data.

## What we fixed (resubmission summary)

- **1.2.2 Billing:** Removed the old Billing API `appSubscriptionCreate` call that
  caused the internal server error. The app now uses Shopify Managed Pricing and
  redirects to the hosted plan-selection page. Fixed the app handle used in the
  pricing URL (`restocked-7`). Created the Starter/Growth/Pro plans and released a
  version so plan selection works.
- **2.1.4 Data accuracy:** Removed all synthetic/sample recommendation fallbacks
  from production. The app now shows only forecasts computed from the store's real
  Shopify orders, and accurate empty states when there is no data to sync.
- **4.5.4 / 4.5.5 Credentials:** No separate login is needed; see testing
  instructions above.

## Reviewer will see real data

The review store has been seeded with apparel products (Size/Color variants) and
order history, so the dashboard shows live variant-level recommendations that
match the store's orders.
