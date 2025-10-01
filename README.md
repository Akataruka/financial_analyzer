
# 📊 Financial Analyzer – Fund Screener Intern Project

A **production-grade financial analysis pipeline** built as part of the Fund-Screener Intern Screening Project.  

This command-line tool ingests stock price & fundamental data, validates it, processes technical/fundamental metrics, detects trading signals, persists results to SQLite, and exports summaries as JSON.

---

## 🚀 Project Overview

The pipeline performs:

1. **Data Ingestion**  
   - Fetches **5 years of daily OHLCV prices** (or shorter if recent IPO).  
   - Retrieves fundamentals (quarterly → annual → info fallback).  
   - Validates with **Pydantic schemas**.

2. **Processing**  
   - Merges daily and quarterly data.  
   - Forward-fills fundamentals between report dates.  
   - Calculates metrics:  
     - **50-day & 200-day SMA**  
     - **52-week high & % from high**  
     - **Book Value per Share (BVPS)**  
     - **Price-to-Book Ratio (P/B)**  
     - **Enterprise Value (EV)**  

3. **Signal Detection**  
   - Detects **Golden Crossovers** (50 SMA crossing above 200 SMA).  
   - Bonus: detects **Death Crosses** (reverse).  

4. **Persistence**  
   - Saves tickers, daily metrics, and signals to **SQLite**.  
   - Idempotent inserts (`INSERT OR REPLACE`) avoid duplicates.  

5. **Delivery**  
   - Runs via **Typer CLI**.  
   - Exports **JSON summary reports** per ticker.

---

## ⚙️ Setup

### Prerequisites
- Python **3.9+**  
- [uv](https://github.com/astral-sh/uv) (recommended)  

### Install
```bash
# Install dependencies
uv sync
````

### Config

Copy and edit config:

```bash
cp config.yaml.example config.yaml
```

Example `config.yaml`:

```yaml
database:
  path: "financial_data.db"

logging:
  level: "INFO"

data_settings:
  historical_period: "5y"
  min_trading_days_for_sma: 200
```

---

## ▶️ Usage

### Run pipeline

```bash
# US stock
uv run python -m financial_analyzer.main run --ticker NVDA --output nvda_analysis.json

# Indian stock
uv run python -m financial_analyzer.main run --ticker RELIANCE.NS --output reliance_analysis.json

# Recent IPO
uv run python -m financial_analyzer.main run --ticker SWIGGY.NS --output swiggy_analysis.json
```

---

## 🧪 Testing

Run unit tests:

```bash
uv run pytest -v
```

Tests cover:

* SMA & ratio calculations
* Golden/Death cross detection
* Validation with Pydantic

---

## 🗄 Database Schema

* **tickers**: basic stock info
* **daily_metrics**: calculated daily metrics
* **signal_events**: detected signals

Unique constraints prevent duplicate entries. Inserts are **idempotent**.

---

## 📝 Design Decisions

* **Frequency mismatch** (daily vs quarterly): handled via **forward-fill** of fundamentals.
* **Unreliable data**: implemented fallbacks (`quarterly_balance_sheet` → `annual_balance_sheet` → `info`).
* **Recent IPOs**: pipeline adapts even with <200 trading days.
* **Cross-market tickers**: US (`AAPL`), India (`RELIANCE.NS`) both supported.
* **Error handling**:

  * Logging (no prints)
  * API failures handled gracefully
  * Partial data processed where possible

---

## 📊 Example Output

```json
{
  "ticker": "NVDA",
  "generated_at": "2025-10-01T10:30:00Z",
  "price_rows_count": 1250,
  "fundamentals_used": "quarterly_balance_sheet",
  "signals": [
    {"date": "2024-06-15", "signal_type": "golden_cross"},
    {"date": "2025-01-10", "signal_type": "death_cross"}
  ]
}
```

---

## ✅ Testing Checklist

* [x] Old US stocks (NVDA, AAPL, MSFT)
* [x] Old Indian stocks (RELIANCE.NS, TCS.NS)
* [x] Recent IPOs (<10 months, US & India)
* [x] Missing fundamentals (fallback)
* [x] Short history (<200 days)
* [x] NaN/partial data handled

---

## 📂 Project Structure

```
financial_analyzer/
├── financial_analyzer/
│   ├── __init__.py
│   ├── config.py
│   ├── data_fetcher.py
│   ├── database.py
│   ├── models.py
│   ├── processor.py
│   ├── signals.py
│   └── main.py
├── tests/
│   ├── conftest.py
│   ├── test_processor.py
│   └── test_signals.py
├── config.yaml.example
├── pyproject.toml
└── README.md
```

---

## 🏆 Notes

* **Logging** helps track API errors, fallbacks, and DB inserts.
* **JSON outputs** included in repo for tested tickers (validation step).
* Project follows **PEP 621 / pyproject.toml**, uses **ruff** for linting, and **pytest** for testing.


