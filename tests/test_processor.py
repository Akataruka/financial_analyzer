# tests/test_processor.py
from src.processor import process_data
import pandas as pd

def test_process_calculations(simple_price_df):
    raw = {"ticker": "TEST", "prices": simple_price_df, "fundamentals": [], "source_info": {}}
    out = process_data(raw)
    # key columns exist
    assert "sma50" in out.columns
    assert "sma200" in out.columns
    assert "52w_high" in out.columns or "52w_high" in out.columns
    # SMA monotonic property: sma200 should be numeric
    assert out["sma200"].notna().any()
