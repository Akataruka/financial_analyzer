# src/processor.py
"""
Process raw_data -> DataFrame with calculated metrics.
Key things:
  - Merge daily prices with forward-filled fundamentals.
  - Compute 50/200-day SMA.
  - Compute 52-week high and % below high.
  - Compute BVPS, P/B, simple EV.
"""
from __future__ import annotations
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
import logging
from decimal import Decimal
from datetime import datetime

logger = logging.getLogger(__name__)


def process_data(raw_data: Dict[str, Any]) -> pd.DataFrame:
    """
    Given the raw_data from fetch_stock_data, return a DataFrame with metrics.
    The returned DataFrame has a 'date' column (datetime) and index is default.
    """
    ticker = raw_data["ticker"]
    prices_df: pd.DataFrame = raw_data["prices"].copy()
    fundamentals = raw_data.get("fundamentals", [])

    # Ensure date column and datetimes
    if "date" not in prices_df.columns:
        raise ValueError("prices must contain 'date' column")
    prices_df["date"] = pd.to_datetime(prices_df["date"])
    prices_df = prices_df.sort_values("date").reset_index(drop=True)

    # Standardize price column names: lower-case we already did in fetcher
    for col in ("open", "high", "low", "close", "adj_close", "volume"):
        if col not in prices_df.columns:
            # Try capitalized names
            if col.capitalize() in prices_df.columns:
                prices_df[col] = prices_df[col.capitalize()]
            else:
                prices_df[col] = np.nan

    # Compute SMAs (rolling). Use min_periods to avoid early values
    prices_df["sma50"] = prices_df["close"].rolling(window=50, min_periods=1).mean()
    prices_df["sma200"] = prices_df["close"].rolling(window=200, min_periods=1).mean()

    # 52-week (approx 252 trading days) high and percent from high
    prices_df["52w_high"] = prices_df["close"].rolling(window=252, min_periods=1).max()
    prices_df["pct_from_52w_high"] = (prices_df["close"] / prices_df["52w_high"] - 1.0) * 100.0

    # Create fundamentals DataFrame (quarterly snapshots)
    if fundamentals:
        fdf = pd.DataFrame(fundamentals)
        # parse as_of
        fdf["as_of"] = pd.to_datetime(fdf["as_of"], errors="coerce")
        # keep useful numeric fields if present
        for col in ["total_stockholder_equity", "total_debt", "cash_and_cash_equivalents", "shares_outstanding", "market_cap"]:
            if col in fdf.columns:
                fdf[col] = pd.to_numeric(fdf[col], errors="coerce")
        # forward-fill: expand quarterly snapshots to daily by merging with nearest prior as_of
        fdf = fdf.sort_values("as_of").drop_duplicates("as_of", keep="last")
        # merge_asof requires both frames sorted by date
        merge_left = prices_df[["date"]].copy().sort_values("date")
        fdf_for_merge = fdf[["as_of", "total_stockholder_equity", "total_debt", "cash_and_cash_equivalents", "shares_outstanding", "market_cap"]].rename(columns={"as_of": "as_of_date"})
        fdf_for_merge = fdf_for_merge.rename(columns={"as_of_date": "as_of"})
        fdf_for_merge = fdf_for_merge.sort_values("as_of")
        # pd.merge_asof expects columns named appropriately
        merge_left["date"] = merge_left["date"].dt.tz_convert("America/New_York")
        fdf_for_merge["as_of"] = pd.to_datetime(fdf_for_merge["as_of"]).dt.tz_localize("America/New_York")

        merged = pd.merge_asof(
            merge_left,
            fdf_for_merge.rename(columns={"as_of": "date"}),
            on="date",
            direction="backward"
        )

        # merged now aligned to daily dates; join back numeric fields
        prices_df = prices_df.merge(merged, on="date", how="left")
        # forward-fill remaining fundamental values
        prices_df[["total_stockholder_equity", "total_debt", "cash_and_cash_equivalents", "shares_outstanding", "market_cap"]] = prices_df[
            ["total_stockholder_equity", "total_debt", "cash_and_cash_equivalents", "shares_outstanding", "market_cap"]
        ].ffill()
    else:
        # no fundamentals; create columns with NaN
        for col in ["total_stockholder_equity", "total_debt", "cash_and_cash_equivalents", "shares_outstanding", "market_cap"]:
            prices_df[col] = np.nan

    # Fundamental ratios:
    # Book Value per Share (BVPS) = total_stockholder_equity / shares_outstanding
    prices_df["bvps"] = prices_df.apply(
        lambda row: (row["total_stockholder_equity"] / row["shares_outstanding"]) if pd.notna(row["total_stockholder_equity"]) and pd.notna(row["shares_outstanding"]) and row["shares_outstanding"] != 0 else np.nan,
        axis=1,
    )
    # Price-to-Book = close / bvps
    prices_df["price_to_book"] = prices_df.apply(
        lambda r: (r["close"] / r["bvps"]) if pd.notna(r["bvps"]) and r["bvps"] != 0 else np.nan, axis=1
    )

    # Enterprise Value (simplified): market_cap + total_debt - cash
    prices_df["enterprise_value"] = prices_df.apply(
        lambda r: r["market_cap"] + r.get("total_debt", 0) - r.get("cash_and_cash_equivalents", 0)
        if pd.notna(r.get("market_cap")) else np.nan,
        axis=1,
    )

    # Add ticker
    prices_df["ticker"] = ticker
    prices_df["generated_at"] = datetime.utcnow().isoformat()

    # final cleanup: keep a subset of useful columns
    keep_cols = [
        "ticker",
        "date",
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "volume",
        "sma50",
        "sma200",
        "52w_high",
        "pct_from_52w_high",
        "bvps",
        "price_to_book",
        "enterprise_value",
        "total_stockholder_equity",
        "total_debt",
        "cash_and_cash_equivalents",
        "shares_outstanding",
        "market_cap",
        "generated_at",
    ]
    # Some columns may be missing; select intersection
    keep_cols = [c for c in keep_cols if c in prices_df.columns]
    out = prices_df[keep_cols].copy()
    return out
