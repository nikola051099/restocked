"""
Test + demo for the forecasting engine.

Generates ~70 weeks of synthetic apparel sales for one hoodie style sold in
5 sizes x 2 colors, with:
  - a realistic size curve (M/L sell most, XS/XXL least),
  - seasonal lift in autumn/winter (hoodies),
  - a growth trend,
  - a deliberate STOCKOUT: Black/M sells out for 6 weeks (sales forced to 0)
    even though true demand is high -> tests stockout-aware logic,
  - Poisson noise.

Then runs the engine and prints the reorder recommendations, and asserts a
few sanity properties so we know it actually works.
"""

from datetime import date, timedelta
import numpy as np
import pandas as pd

try:
    from .engine import ForecastEngine, ForecastConfig
except ImportError:  # Allow `python test_engine.py` from this folder.
    from engine import ForecastEngine, ForecastConfig

RNG = np.random.default_rng(42)

SIZES = ["XS", "S", "M", "L", "XL"]
# true relative demand by size (the "size curve")
SIZE_CURVE = {"XS": 0.08, "S": 0.20, "M": 0.32, "L": 0.25, "XL": 0.15}
COLORS = ["Black", "Olive"]
COLOR_WEIGHT = {"Black": 0.62, "Olive": 0.38}

N_WEEKS = 70
BASE_WEEKLY_STYLE_DEMAND = 60     # units/week across all variants at season baseline
TODAY = date(2026, 6, 22)         # a Monday


def seasonal_multiplier(week_start: date) -> float:
    # hoodies: peak in Oct-Jan, trough in Jun-Jul
    m = week_start.month
    table = {1: 1.35, 2: 1.15, 3: 0.95, 4: 0.8, 5: 0.7, 6: 0.6,
             7: 0.6, 8: 0.8, 9: 1.1, 10: 1.4, 11: 1.5, 12: 1.45}
    return table[m]


def generate():
    start = TODAY - timedelta(weeks=N_WEEKS)
    weeks = [start + timedelta(weeks=i) for i in range(N_WEEKS)]

    rows = []
    variant_rows = []
    in_stock_weeks = {}

    for color in COLORS:
        for size in SIZES:
            vid = f"hoodie-{color}-{size}".lower()
            variant_rows.append({
                "variant_id": vid,
                "product_id": "hoodie",
                "size": size,
                "color": color,
                "current_stock": 0,        # set below
                "in_stock_weeks": N_WEEKS,  # adjusted for the stockout case
            })

    stockout_vid = "hoodie-black-m"
    stockout_weeks = set(range(N_WEEKS - 14, N_WEEKS - 8))  # 6-week gap, recent-ish

    for wi, wk in enumerate(weeks):
        trend = 1.0 + 0.010 * wi            # ~ +1%/week growth
        seas = seasonal_multiplier(wk)
        for color in COLORS:
            for size in SIZES:
                vid = f"hoodie-{color}-{size}".lower()
                mean = (BASE_WEEKLY_STYLE_DEMAND
                        * SIZE_CURVE[size] * COLOR_WEIGHT[color]
                        * seas * trend)
                qty = RNG.poisson(max(mean, 0.01))

                if vid == stockout_vid and wi in stockout_weeks:
                    qty = 0  # sold out -> 0 sales despite high true demand

                if qty > 0:
                    rows.append({"order_date": wk, "variant_id": vid,
                                 "quantity": int(qty)})

    orders = pd.DataFrame(rows)
    variants = pd.DataFrame(variant_rows)

    # in_stock_weeks reflects the stockout for Black/M
    variants.loc[variants["variant_id"] == stockout_vid, "in_stock_weeks"] = \
        N_WEEKS - len(stockout_weeks)

    # set current stock: give everyone ~2 weeks of average cover, but make
    # Black/M critically low to prove urgency detection
    recent = orders[orders["order_date"] >= (TODAY - timedelta(weeks=8))]
    avg8 = recent.groupby("variant_id")["quantity"].sum() / 8.0
    stock = {}
    for vid in variants["variant_id"]:
        rate = float(avg8.get(vid, 0.0))
        stock[vid] = int(round(rate * 2))
    stock[stockout_vid] = 3  # critically low on the bestseller size
    variants["current_stock"] = variants["variant_id"].map(stock)

    return orders, variants, stockout_vid


def main():
    orders, variants, stockout_vid = generate()
    print(f"Generated {len(orders)} order lines across "
          f"{variants['variant_id'].nunique()} variants over {N_WEEKS} weeks.\n")

    cfg = ForecastConfig(lead_time_days=30, review_period_days=14,
                         service_level=0.95)
    engine = ForecastEngine(cfg)
    recs = engine.recommend(orders, variants, today=TODAY)

    show_cols = ["size", "color", "current_stock", "avg_weekly_demand",
                 "seasonal_factor", "days_of_cover_left", "stockout_risk",
                 "recommended_order_qty", "size_curve_share"]
    pd.set_option("display.width", 160)
    pd.set_option("display.max_columns", 30)
    print("RECOMMENDATIONS (sorted by urgency):\n")
    print(recs[show_cols].to_string(index=False))

    print("\n--- 'Show your math' for the sold-out bestseller (Black/M) ---")
    row = recs[recs["variant_id"] == stockout_vid].iloc[0]
    print(row["reasoning"])
    print("components:", row["components"])

    # -------------------- sanity assertions --------------------------------- #
    print("\nRunning sanity checks...")

    # 1) recovered the size curve roughly: M share > S share > XS share (Black)
    black = recs[recs["color"] == "Black"].set_index("size")
    assert black.loc["M", "size_curve_share"] > black.loc["S", "size_curve_share"] > \
           black.loc["XS", "size_curve_share"], "size curve not recovered"
    print("  [ok] size curve recovered (M > S > XS share)")

    # 2) stockout-aware: Black/M forecast not crushed by the 6 zero weeks.
    #    Its weekly demand should still be the largest among Black sizes.
    assert black["avg_weekly_demand"].idxmax() == "M", \
        "stockout suppressed the bestseller forecast"
    print("  [ok] stockout-aware: Black/M still forecast as the top size")

    # 3) urgency: the critically-low bestseller is flagged imminent + biggest order
    assert row["stockout_risk"] == "imminent", "did not flag imminent stockout"
    assert row["recommended_order_qty"] == recs["recommended_order_qty"].max(), \
        "bestseller did not get the largest reorder"
    print("  [ok] urgency: Black/M flagged imminent with the largest reorder qty")

    # 4) seasonality: forecasting in June (trough) should generally not inflate
    assert (recs["seasonal_factor"] < 1.2).mean() > 0.6, "seasonality off"
    print("  [ok] seasonality applied (June trough not inflated)")

    # 5) no negative or absurd recommendations
    assert (recs["recommended_order_qty"] >= 0).all()
    assert (recs["avg_weekly_demand"] >= 0).all()
    print("  [ok] all recommendations non-negative and finite")

    print("\nAll checks passed. Engine works.")


if __name__ == "__main__":
    main()
