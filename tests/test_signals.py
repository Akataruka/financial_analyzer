# tests/test_signals.py
import pandas as pd
from src.signals import detect_golden_crossover, detect_death_cross

def test_signal_detection_simple():
    # create a scenario where sma50 crosses above sma200 on day 3
    df = pd.DataFrame({
        "date": pd.date_range("2023-01-01", periods=6),
        "sma50": [1, 1, 2, 3, 4, 5],
        "sma200": [2, 2, 2, 2, 2, 2],
    })
    golden = detect_golden_crossover(df)
    # Expect cross when sma50 moves from <= sma200 to > sma200 (day index 2 -> day3)
    assert len(golden) >= 1

    # death cross: create reverse
    df2 = pd.DataFrame({
        "date": pd.date_range("2023-01-01", periods=6),
        "sma50": [5,4,3,2,1,0],
        "sma200": [2,2,2,2,2,2],
    })
    death = detect_death_cross(df2)
    assert len(death) >= 1
