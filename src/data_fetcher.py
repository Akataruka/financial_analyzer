# src/data_fetcher.py
"""
Data ingestion: fetch_stock_data(ticker) -> dict
Uses yfinance and Pydantic models for validation and fallback strategies.
"""
from __future__ import annotations
import logging
from typing import Dict, Any
import yfinance as yf
from datetime import datetime
from decimal import Decimal
from .models import FundamentalsQuarter
from .config import load_config

logger = logging.getLogger(__name__)
CONFIG = load_config()


def _decimal_or_none(x):
    if x is None:
        return None
    try:
        return Decimal(str(x))
    except Exception:
        return None


def fetch_stock_data(ticker: str, period: str | None = None) -> Dict[str, Any]:
    """
    Fetch price history and fundamental snapshots for ticker.

    Returns raw dict:
      {
        "ticker": "NVDA",
        "prices": pd.DataFrame,  # with Date index
        "fundamentals": list[FundamentalsQuarter dicts],
        "source_info": {"used": "...", "notes": "..."}
      }
    """
    if period is None:
        period = CONFIG["data_settings"].get("historical_period", "5y")

    logger.info("Fetching %s with period=%s", ticker, period)
    t = yf.Ticker(ticker)

    # 1) Fetch prices
    try:
        prices = t.history(period=period, auto_adjust=False)
    except Exception as e:
        logger.exception("Failed to fetch price history for %s: %s", ticker, e)
        raise

    # Normalize prices DataFrame: ensure expected columns and types
    # upstream code expects Date index named 'Date'
    prices = prices.rename_axis("date").reset_index()
    # later processing expects 'Close' etc., but we'll standardize to lowercase
    prices.columns = [c.lower().replace(" ", "_") for c in prices.columns]

    # 2) Fetch fundamentals with fallback strategy
    source_used = None
    fundamentals = []

    # Try quarterly financials (balance sheet, cashflow)
    try:
        qb = t.quarterly_balance_sheet
        if isinstance(qb, dict) or hasattr(qb, "columns"):
            # yfinance returns DataFrame with columns as dates; we'll convert to records
            if getattr(qb, "empty", False):
                qb = None
        if qb is not None and getattr(qb, "empty", True) is False:
            source_used = "quarterly_balance_sheet"
            # qb is a DataFrame with columns as periods
            for col in qb.columns:
                col_data = qb[col]
                f = FundamentalsQuarter(
                    as_of=str(col),
                    total_stockholder_equity=_decimal_or_none(col_data.get("Total Stockholder Equity") if isinstance(col_data, dict) else None),
                    extra={"raw_column": str(col)}
                )
                fundamentals.append(f.dict())
    except Exception:
        logger.debug("quarterly_balance_sheet not usable for %s", ticker)

    # If no quarterly, try annual balance sheet
    if not fundamentals:
        try:
            ab = t.balance_sheet
            if ab is not None and getattr(ab, "empty", True) is False:
                source_used = "annual_balance_sheet"
                for col in ab.columns:
                    col_data = ab[col]
                    f = FundamentalsQuarter(
                        as_of=str(col),
                        total_stockholder_equity=_decimal_or_none(col_data.get("Total Stockholder Equity") if isinstance(col_data, dict) else None),
                        extra={"raw_column": str(col)}
                    )
                    fundamentals.append(f.dict())
        except Exception:
            logger.debug("annual balance_sheet not usable for %s", ticker)

    # Finally use ticker.info as fallback
    if not fundamentals:
        try:
            info = t.info or {}
            # Use info snapshot once
            f = FundamentalsQuarter(
                as_of=datetime.utcnow().isoformat(),
                total_stockholder_equity=_decimal_or_none(info.get("totalStockholderEquity") or info.get("totalAssets")),
                cash_and_cash_equivalents=_decimal_or_none(info.get("cash")),
                total_debt=_decimal_or_none(info.get("totalDebt") or info.get("debt")),
                shares_outstanding=_decimal_or_none(info.get("sharesOutstanding")),
                market_cap=_decimal_or_none(info.get("marketCap")),
                extra={"info_keys": list(info.keys())[:10]},
            )
            fundamentals.append(f.dict())
            source_used = "info"
        except Exception:
            logger.exception("ticker.info failed for %s", ticker)

    source_info = {"used": source_used or "none", "fetched_at": datetime.utcnow().isoformat()}

    return {
        "ticker": ticker,
        "prices": prices,
        "fundamentals": fundamentals,
        "source_info": source_info,
    }
