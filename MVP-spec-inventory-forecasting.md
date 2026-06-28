# MVP Spec — Shopify Demand-Forecasting App

*Validated from Shopify App Store reviews, pricing, and the Stocky deprecation. Written June 27, 2026.*

---

## The one-line decision

Build a **variant-level demand-forecasting + reorder app for multi-variant stores (apparel, footwear, anything sold in sizes/colors)**, launched into the Stocky migration. The differentiator is **forecast accuracy at the size/variant level** — the thing your modeling skills do well and that every existing tool does naively.

This is a sharpening of "build a forecasting app," forced by what the research found: the generic lane is already taken.

---

## Why the wedge moved (read this first)

I went in expecting "a simpler, cheaper Stocky replacement for small stores" to be open. It is **not**. The validation found:

- **Stockie** ($4.99–$59.99/mo, **5.0 stars from 102 reviews, zero reviews below 4 stars**) already owns the small-store-Stocky-replacement position and is loved for its support and migration help.
- The enterprise end is held by **Prediko** ($49–$199/mo, 4.9/229) and **Assisty** ($19–$239/mo, 4.9/342).
- New entrants keep piling into the *generic* lane (Rewize, Bee, Logistified, "Purchase Order Hero — the Stocky replacement," etc.).

So "cheaper and simpler" is a dead wedge. But one thing is genuinely missing:

- A search for **"apparel size forecasting" returns no dedicated product** — only size-*chart* apps and the same generic forecasters. None of the forecasters forecast at the **variant (size/color) level**; they forecast a product and split it crudely. For apparel that's the whole game: you don't run out of "the t-shirt," you run out of **Medium Black** while **XXL White** sits as dead stock.

That gap is defensible because it's a **real modeling problem** (size-curve / intermittent demand per variant), not a UI feature anyone can copy in a weekend. It's your edge.

---

## Market map (what's taken vs. open)

| Lane | Who owns it | Verdict |
|---|---|---|
| Cheap, simple small-store forecaster | Stockie (5.0/102) | Taken, beloved — avoid |
| Mid/enterprise forecaster + POs | Prediko, Assisty | Taken, entrenched |
| Profit analytics | TrueProfit + 30 others | Saturated, support-war — avoid |
| Generic reports | Report Pundit, Data Export (5.0, 1800+) | Taken — avoid |
| **Variant/size-level forecasting (apparel)** | **Nobody dedicated** | **Open — your wedge** |
| Bundle/kit forecasting | Prediko (poorly) | Half-open — secondary angle |
| BOM/raw-material forecasting (makers) | Small, fussy, low-rated apps | Open but small market |

---

## The Stocky timeline (your tailwind and your clock)

- **Jul 7, 2025** — Stocky dropped inventory transfers + min/max forecasting.
- **Feb 2, 2026** — Stocky removed from the App Store (no reinstall, no data recovery).
- **Aug 31, 2026** — full shutdown. *That is ~2 months from today.*

Shopify's native Admin replacement deliberately **omits**: demand forecasting, automated reorder points, velocity-based restock, safety-stock buffers, supplier lead-time tracking, weekly inventory email reports, and PO workflows tied to forecasts. That omission is a durable, long-tail opportunity — merchants will keep discovering native isn't enough for months *after* August.

**Honest timing read:** you will likely launch around or just after the shutdown. You miss the first migration rush (Stockie/Prediko already caught it) but land in the "native Admin isn't enough, what now?" wave — which is fine, because your wedge isn't "replace Stocky generically," it's "do the size/variant forecasting none of them do."

---

## Target segment (be this specific)

**Shopify apparel/footwear/accessory brands with 500–10,000 variants, doing roughly $200k–$2M/year, who reorder from suppliers (not pure print-on-demand).**

Why this segment:
- They feel size-curve pain acutely (wrong-size dead stock is their #1 margin leak).
- Big enough to pay, small enough that Prediko's enterprise pricing/complexity annoys them.
- Established sales history exists (forecasting needs it — brand-new stores are *not* your buyer).

---

## MVP — the 3–4 must-have features for v1

Keep v1 ruthlessly narrow. Each feature below maps to a documented complaint or a Stocky gap.

1. **Variant-level demand forecast.** Forecast each SKU/variant separately using real sales history, with seasonality and trend. This is the headline and the moat — get this visibly more accurate than product-level tools. *(Maps to: the empty "apparel size forecasting" gap.)*

2. **Reorder recommendations with lead time + safety stock.** "Order N units of Medium Black by [date]." Configurable supplier lead time and safety buffer. *(Maps to: exactly the features Shopify Admin dropped.)*

3. **Show your math / trust panel.** For every recommendation, show *why*: the sales trend, the forecast curve, the assumptions. This is non-negotiable — across every app, the recurring complaint is "I had to double-check the numbers against Shopify." Winning trust is how a solo beats funded teams. *(Maps to: accuracy/trust complaints in Assisty, Prediko, Triple Whale.)*

4. **Low-stock + reorder email/Slack alerts.** Scheduled digest: what to reorder this week. Simple, but it's the habit-forming hook that keeps the app in their routine. *(Maps to: a core Stocky feature Admin omits.)*

That's it. Four things, done genuinely well, for one type of store.

---

## Deliberately NOT in v1 (cut these on purpose)

- Full purchase-order management / receiving workflow (Stockie/Prediko's deep moat — don't fight it yet).
- Multi-warehouse / multi-location balancing.
- Bundles/BOM/raw materials (tempting, but a separate wedge — revisit later).
- 3PL/WMS integrations.
- Landed-cost / margin accounting.
- A "100+ reports" builder.

Every one of these expands support burden — the thing most likely to sink a solo founder. Resist.

---

## Designing around the solo-founder killer: support & trust

The data's clearest signal: **inventory apps live or die on support responsiveness and number-trust**, and that's the hardest thing for one person. Mitigate by design, not by heroics:

- Narrow segment + narrow feature set = fewer edge cases = less support.
- The "show your math" panel pre-empts the #1 support ticket ("are these numbers right?").
- Self-serve onboarding (sample forecast on install, no mandatory demo call).
- In-app docs and a clear "how the forecast works" page.

---

## Pricing

Anchor between Stockie and Prediko, justified by accuracy/specialization:

- **Starter ~$19/mo** — forecasting + alerts, up to ~1,000 variants.
- **Growth ~$39/mo** — full variant forecasting + reorder + lead/safety settings, up to ~5,000 variants.
- **Pro ~$79/mo** — 10,000 variants, Slack, priority.

14-day free trial. Price *higher* than instinct — B2B underpricing signals low value and starves you. (Stockie tops out at $59.99; Prediko at $199. You have room.)

---

## 90-day goal (realistic)

Not $100/day. The goal is: **live app + first 5–10 paying apparel stores + first reviews + proof the forecast beats their old method.** That's the leading indicator. $100/day follows in ~4–8 months if the accuracy story lands.

---

## The ONE validation step before you write code

Confirm apparel merchants will *pay* for size-level forecasting specifically. Concrete checks:
1. Read 1–3★ reviews of Prediko/Assisty/Stockie filtering for apparel stores complaining about variant/size handling.
2. Find 5–10 apparel merchants on r/shopify or forums describing the dead-stock-by-size problem in their own words.
3. Ideally, talk to 3 apparel store owners (DM, Reddit) and ask how they decide reorders by size today.

If you can't find that pain expressed in merchants' own words, the wedge is theory — pick the bundle or BOM angle instead. If you can, build.

---

## Honest risk summary

- **Crowded category, fast.** New forecasters launch weekly. Your defense is the variant-accuracy moat, not features.
- **Incumbents can add it.** Prediko could ship size-level forecasting. Your edge is being the *specialist* apparel brands trust, and being faster/better at the one thing.
- **Accuracy bar is unforgiving.** A wrong forecast loses the merchant money and earns a 1★ review the same week. The "show your math" panel and a conservative, explainable model matter more than a fancy black box.
- **Timing.** You're late to the first migration rush; you're on time for the "native isn't enough" long tail.
