# src/signals.py
"""
Detect trading signals: golden crossover (50-day SMA crosses above 200-day SMA)
and death cross (50 drops below 200).
"""
from __future__ import annotations
from typing import List
import pandas as pd
import logging
from datetime import date

logger = logging.getLogger(__name__)


def detect_golden_crossover(df: pd.DataFrame, sma50_col: str = "sma50", sma200_col: str = "sma200") -> List[str]:
    """
    Return list of ISO dates where golden crossover occurred.
    Uses vectorized approach:
      golden = (sma50 > sma200) & (sma50.shift(1) <= sma200.shift(1))
    """
    if sma50_col not in df.columns or sma200_col not in df.columns:
        logger.warning("SMA columns not present for signal detection")
        return []

    s50 = df[sma50_col]
    s200 = df[sma200_col]

    cond = (s50 > s200) & (s50.shift(1) <= s200.shift(1))
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    dates = df.loc[cond, "date"].dt.date.astype(str).tolist()
    return dates


def detect_death_cross(df: pd.DataFrame, sma50_col: str = "sma50", sma200_col: str = "sma200") -> List[str]:
    """Return list of ISO dates for death cross events."""
    if sma50_col not in df.columns or sma200_col not in df.columns:
        return []
    s50 = df[sma50_col]
    s200 = df[sma200_col]
    cond = (s50 < s200) & (s50.shift(1) >= s200.shift(1))
    dates = df.loc[cond, "date"].dt.date.astype(str).tolist()
    return dates
