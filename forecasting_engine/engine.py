"""
Variant-level demand forecasting + reorder engine.

This is the core IP of the app: it forecasts demand for each individual variant
(e.g. "T-Shirt / Black / M") rather than for the parent product, then turns that
forecast into an explainable reorder recommendation.

Design goals
------------
1. Variant-level. We never split a product forecast evenly across sizes; each
   variant gets its own forecast. This is the whole differentiator.
2. Stockout-aware. "No sales" during an out-of-stock week is NOT "no demand".
   If availability data is provided we exclude unavailable weeks when measuring
   demand, so we don't under-forecast popular sizes that keep selling out.
3. Robust on sparse data. Apparel variants often have thin, lumpy histories.
   We pick the method per-variant based on how much signal exists.
4. Explainable. Every recommendation carries a `reasoning` string and the raw
   components behind it ("show your math"), because trust is what makes a
   merchant act on the number.

Dependencies: pandas, numpy only (kept deliberately light).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date
import math

import numpy as np
import pandas as pd


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

@dataclass
class ForecastConfig:
    # Planning horizon for the recommendation, in days. Usually the supplier
    # lead time: "how much will I sell before a new order can arrive?"
    lead_time_days: int = 30

    # Review period: how often the merchant reorders (days). Order enough to
    # cover lead time + the gap until the next review.
    review_period_days: int = 14

    # Target service level (probability of NOT stocking out in the cycle).
    # 0.95 -> z ~= 1.645. Higher = more safety stock = fewer stockouts, more cash tied up.
    service_level: float = 0.95

    # Weeks of history considered "enough" to fit seasonality (1 year).
    seasonal_min_weeks: int = 52

    # Weeks of history considered "enough" for a trend/level model.
    trend_min_weeks: int = 8

    # EWMA smoothing factor for level (0-1). Higher = reacts faster to recent change.
    level_alpha: float = 0.3

    # A variant selling on fewer than this fraction of in-stock weeks is treated
    # as "intermittent" (lumpy) and gets a more conservative method.
    intermittent_threshold: float = 0.35


# Z-scores for common service levels (normal approximation).
_Z_TABLE = {0.50: 0.0, 0.80: 0.8416, 0.85: 1.0364, 0.90: 1.2816,
            0.95: 1.6449, 0.975: 1.9600, 0.98: 2.0537, 0.99: 2.3263}


def _z_for_service_level(sl: float) -> float:
    # nearest tabulated z; fine for planning purposes
    key = min(_Z_TABLE, key=lambda k: abs(k - sl))
    return _Z_TABLE[key]


# --------------------------------------------------------------------------- #
# Result object
# --------------------------------------------------------------------------- #

@dataclass
class VariantRecommendation:
    variant_id: str
    product_id: str
    size: str
    color: str
    current_stock: int

    # Forecast outputs
    avg_weekly_demand: float
    weekly_demand_std: float
    method: str
    trend_per_week: float
    seasonal_factor: float          # applied for the upcoming lead-time window

    # Planning outputs
    lead_time_demand: float
    safety_stock: float
    reorder_point: float
    recommended_order_qty: int
    days_of_cover_left: float
    stockout_risk: str              # "imminent" | "soon" | "ok"

    # Size-curve context (variant share of its product's demand)
    size_curve_share: float

    reasoning: str = ""
    components: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------- #
# Core engine
# --------------------------------------------------------------------------- #

class ForecastEngine:
    """
    Usage:
        engine = ForecastEngine(config)
        recs = engine.recommend(orders_df, variants_df, today=date(...))

    orders_df columns (one row per sold unit-line):
        order_date (datetime-like), variant_id, quantity
    variants_df columns (one row per variant):
        variant_id, product_id, size, color, current_stock
        [optional] in_stock_weeks  -> int count of weeks the variant was available
                                       (lets us be stockout-aware); if absent we
                                       assume it was available the whole window.
    """

    def __init__(self, config: ForecastConfig | None = None):
        self.cfg = config or ForecastConfig()

    # ----- public ----------------------------------------------------------- #

    def recommend(self, orders_df: pd.DataFrame, variants_df: pd.DataFrame,
                  today: date | None = None) -> pd.DataFrame:
        today = today or date.today()
        weekly = self._weekly_demand_matrix(orders_df, today)

        # product-level totals for size-curve share
        prod_totals = self._product_demand_totals(weekly, variants_df)

        recs = []
        for _, v in variants_df.iterrows():
            series = weekly.get(v["variant_id"], pd.Series(dtype=float))
            rec = self._recommend_one(v, series, prod_totals)
            recs.append(rec.to_dict())

        out = pd.DataFrame(recs)
        if not out.empty:
            rank_map = {"imminent": 0, "soon": 1, "ok": 2}
            out["_rank"] = out["stockout_risk"].map(rank_map).fillna(3)
            out = (out.sort_values(["_rank", "recommended_order_qty"],
                                   ascending=[True, False])
                      .drop(columns=["_rank"])
                      .reset_index(drop=True))
        return out

    # ----- demand preparation ---------------------------------------------- #

    def _weekly_demand_matrix(self, orders_df: pd.DataFrame,
                              today: date) -> dict[str, pd.Series]:
        if orders_df.empty:
            return {}
        df = orders_df.copy()
        df["order_date"] = pd.to_datetime(df["order_date"])
        df = df[df["order_date"].dt.date <= today]
        # ISO week buckets
        df["week"] = df["order_date"].dt.to_period("W").dt.start_time

        grouped = (df.groupby(["variant_id", "week"])["quantity"]
                     .sum().reset_index())

        full_weeks = pd.date_range(
            end=pd.Timestamp(today), periods=self.cfg.seasonal_min_weeks + 8,
            freq="W-MON"
        ).normalize()

        series_by_variant: dict[str, pd.Series] = {}
        for vid, g in grouped.groupby("variant_id"):
            s = g.set_index("week")["quantity"].sort_index()
            s = s.reindex(full_weeks, fill_value=0.0)  # explicit zero weeks
            series_by_variant[vid] = s
        return series_by_variant

    def _product_demand_totals(self, weekly: dict[str, pd.Series],
                               variants_df: pd.DataFrame) -> dict[str, float]:
        totals: dict[str, float] = {}
        vid_to_prod = dict(zip(variants_df["variant_id"], variants_df["product_id"]))
        for vid, s in weekly.items():
            prod = vid_to_prod.get(vid)
            if prod is None:
                continue
            totals[prod] = totals.get(prod, 0.0) + float(s.sum())
        return totals

    # ----- per-variant model ------------------------------------------------ #

    def _recommend_one(self, v: pd.Series, series: pd.Series,
                       prod_totals: dict[str, float]) -> VariantRecommendation:
        cfg = self.cfg
        vid = v["variant_id"]
        current_stock = int(v.get("current_stock", 0) or 0)

        # how many weeks was this variant actually available?
        in_stock_weeks = v.get("in_stock_weeks", np.nan)
        nonzero = series[series > 0]
        weeks_with_history = int((series.index >= series[series > 0].index.min()).sum()) \
            if not nonzero.empty else 0

        # ---- pick a method based on available signal --------------------- #
        if weeks_with_history < cfg.trend_min_weeks or series.sum() < 3:
            method, level, trend, seas, std = self._method_sparse(series)
        elif weeks_with_history >= cfg.seasonal_min_weeks:
            method, level, trend, seas, std = self._method_seasonal(series)
        else:
            method, level, trend, seas, std = self._method_trend(series)

        # stockout-aware uplift: if the variant sold on a small share of its
        # in-stock weeks but always sold out fast, the raw mean understates it.
        level = self._stockout_adjust(level, series, in_stock_weeks)

        # ---- planning math ----------------------------------------------- #
        weeks_cover = (cfg.lead_time_days + cfg.review_period_days) / 7.0
        lead_weeks = cfg.lead_time_days / 7.0

        # expected demand over the protection window, with trend + seasonality
        base_window_demand = max(0.0, level * weeks_cover
                                 + trend * (weeks_cover ** 2) / 2.0)
        window_demand = base_window_demand * seas

        z = _z_for_service_level(cfg.service_level)
        # safety stock over the protection window
        safety = z * std * math.sqrt(max(weeks_cover, 1e-9))

        reorder_point = level * seas * lead_weeks + safety
        recommended = max(0.0, window_demand + safety - current_stock)
        recommended_qty = int(math.ceil(recommended))

        # days of cover left at current run-rate
        weekly_rate = max(level * seas, 1e-9)
        days_left = (current_stock / weekly_rate) * 7.0

        if days_left <= cfg.lead_time_days:
            risk = "imminent"
        elif days_left <= cfg.lead_time_days + cfg.review_period_days:
            risk = "soon"
        else:
            risk = "ok"

        # size-curve share
        prod = v["product_id"]
        prod_total = prod_totals.get(prod, 0.0)
        share = float(series.sum() / prod_total) if prod_total > 0 else 0.0

        reasoning = self._build_reasoning(
            v, method, level, trend, seas, current_stock,
            window_demand, safety, recommended_qty, days_left, risk, share
        )

        rec = VariantRecommendation(
            variant_id=vid,
            product_id=prod,
            size=str(v.get("size", "")),
            color=str(v.get("color", "")),
            current_stock=current_stock,
            avg_weekly_demand=round(level, 3),
            weekly_demand_std=round(std, 3),
            method=method,
            trend_per_week=round(trend, 4),
            seasonal_factor=round(seas, 3),
            lead_time_demand=round(level * seas * lead_weeks, 2),
            safety_stock=round(safety, 2),
            reorder_point=round(reorder_point, 2),
            recommended_order_qty=recommended_qty,
            days_of_cover_left=round(days_left, 1),
            stockout_risk=risk,
            size_curve_share=round(share, 4),
            reasoning=reasoning,
            components={
                "weeks_with_history": weeks_with_history,
                "weeks_cover": round(weeks_cover, 2),
                "z_service_level": z,
                "window_demand": round(window_demand, 2),
                "raw_weekly_mean": round(float(series.tail(cfg.seasonal_min_weeks).mean()), 3),
            },
        )
        return rec

    # ----- forecasting methods --------------------------------------------- #

    def _method_seasonal(self, series: pd.Series):
        """Level + linear trend + week-of-year seasonal indices.
        Stockout-robust: for variants that sell most weeks, zero weeks are
        treated as stockouts/noise and excluded from level + variability, so a
        sold-out bestseller is not under-forecast. The trend is measured on a
        deseasonalised window so an off-season dip isn't read as a decline."""
        cfg = self.cfg
        s = series.astype(float)

        # seasonal indices by ISO week-of-year (multiplicative)
        idx = s.index.isocalendar().week.values
        dfa = pd.DataFrame({"woy": idx, "y": s.values})
        overall = dfa["y"].mean() or 1e-9
        woy_mean = dfa.groupby("woy")["y"].mean()
        seasonal_indices = (woy_mean / overall).to_dict()

        # stockout-robust basis for level + std
        recent = s.tail(cfg.seasonal_min_weeks)
        sell_rate = float((recent > 0).mean())
        basis = recent[recent > 0] if sell_rate >= 0.5 else recent
        if len(basis) == 0:
            basis = recent
        level = float(basis.ewm(alpha=cfg.level_alpha).mean().iloc[-1])
        std = float(basis.std(ddof=0)) if len(basis) > 1 else 0.0

        # trend on a DESEASONALISED last-26-week window
        tailn = s.tail(26)
        deseason = [
            (y / (seasonal_indices.get(int(ts.isocalendar().week), 1.0) or 1.0))
            for ts, y in tailn.items()
        ]
        trend = self._linear_slope(np.array(deseason, dtype=float))

        # seasonal factor for the upcoming lead-time window (next ~4 weeks)
        upcoming = self._upcoming_weeks_of_year(s.index[-1], n=4)
        factors = [seasonal_indices.get(w, 1.0) for w in upcoming]
        seas = float(np.clip(np.mean(factors), 0.3, 3.0))

        return "seasonal+trend", max(level, 0.0), trend, seas, std

    def _method_trend(self, series: pd.Series):
        """Level + trend, no seasonality (not enough history). Stockout-robust:
        frequent sellers exclude zero weeks from level + variability."""
        cfg = self.cfg
        s = series.astype(float)
        recent = s[s.index >= s[s > 0].index.min()] if (s > 0).any() else s
        sell_rate = float((recent > 0).mean()) if len(recent) else 0.0
        basis = recent[recent > 0] if sell_rate >= 0.5 else recent
        if len(basis) == 0:
            basis = recent
        level = float(basis.ewm(alpha=cfg.level_alpha).mean().iloc[-1])
        trend = self._linear_slope(recent.tail(12).values)
        std = float(basis.std(ddof=0)) if len(basis) > 1 else 0.0
        return "trend", max(level, 0.0), trend, 1.0, std

    def _method_sparse(self, series: pd.Series):
        """Intermittent / very thin demand: conservative mean, no trend."""
        s = series.astype(float)
        active = s[s.index >= s[s > 0].index.min()] if (s > 0).any() else s
        if active.empty:
            return "sparse", 0.0, 0.0, 1.0, 0.0
        # Croston-style: average size of a sale / average interval between sales
        nonzero = active[active > 0]
        avg_size = float(nonzero.mean()) if not nonzero.empty else 0.0
        interval = len(active) / max(len(nonzero), 1)
        level = avg_size / max(interval, 1.0)
        std = float(active.std(ddof=0)) or avg_size
        return "sparse", max(level, 0.0), 0.0, 1.0, std

    # ----- helpers ---------------------------------------------------------- #

    @staticmethod
    def _linear_slope(arr: np.ndarray) -> float:
        arr = np.asarray(arr, dtype=float)
        n = len(arr)
        if n < 3:
            return 0.0
        x = np.arange(n)
        x_mean, y_mean = x.mean(), arr.mean()
        denom = ((x - x_mean) ** 2).sum()
        if denom == 0:
            return 0.0
        return float(((x - x_mean) * (arr - y_mean)).sum() / denom)

    @staticmethod
    def _upcoming_weeks_of_year(last_ts: pd.Timestamp, n: int) -> list[int]:
        weeks = []
        for i in range(1, n + 1):
            weeks.append(int((last_ts + pd.Timedelta(weeks=i)).isocalendar().week))
        return weeks

    def _stockout_adjust(self, level: float, series: pd.Series,
                         in_stock_weeks) -> float:
        """If the variant was only available a fraction of the window but sold
        whenever in stock, scale the per-week rate up to true demand."""
        if pd.isna(in_stock_weeks) or in_stock_weeks <= 0:
            return level
        observed_weeks = int((series > 0).sum())
        if observed_weeks == 0:
            return level
        # demand rate measured only over weeks it was actually available
        total = float(series.sum())
        true_rate = total / max(int(in_stock_weeks), 1)
        # take the higher of EWMA level and availability-adjusted rate
        return max(level, true_rate)

    def _build_reasoning(self, v, method, level, trend, seas, stock,
                         window_demand, safety, qty, days_left, risk, share) -> str:
        name = f'{v.get("size","")}/{v.get("color","")}'.strip("/")
        bits = [
            f'Variant {name}: ~{level:.1f} units/week ({method}).',
        ]
        if abs(trend) > 0.2:
            direction = "rising" if trend > 0 else "falling"
            bits.append(f"demand {direction} ({trend:+.2f}/wk).")
        if abs(seas - 1.0) > 0.1:
            updown = "above" if seas > 1 else "below"
            bits.append(f"upcoming season {updown} average (x{seas:.2f}).")
        bits.append(
            f"Stock {stock} = ~{days_left:.0f} days cover; "
            f"need ~{window_demand:.0f} over lead+review + {safety:.0f} safety."
        )
        if qty > 0:
            bits.append(f"-> reorder {qty} units ({risk}).")
        else:
            bits.append("-> no reorder needed.")
        bits.append(f"This size is {share*100:.0f}% of the style's demand.")
        return " ".join(bits)
