# tests/conftest.py
import pytest
import pandas as pd
from datetime import datetime, timedelta


import sys
import pathlib

# Add src/ folder to sys.path
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / "src"))


@pytest.fixture
def simple_price_df():
    # create 300 days of synthetic prices to allow 200-day SMA
    start = datetime(2023, 1, 1)
    rows = []
    price = 100.0
    for i in range(300):
        d = start + timedelta(days=i)
        # skip weekends for realism: but for test keep continuous dates
        openp = price
        close = price + (i % 5 - 2) * 0.5
        high = max(openp, close) + 1
        low = min(openp, close) - 1
        rows.append({"date": pd.to_datetime(d), "open": openp, "high": high, "low": low, "close": close, "adj_close": close, "volume": 1000})
        price = close
    df = pd.DataFrame(rows)
    return df
