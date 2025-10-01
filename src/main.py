# src/main.py
"""
CLI entrypoint built with Click. Orchestrates:
  - init DB
  - fetch data
  - process metrics
  - detect signals
  - persist to DB
  - export JSON
"""
from __future__ import annotations

import pandas as pd
import logging
import json
import click
from datetime import datetime

from .config import load_config
from .data_fetcher import fetch_stock_data
from .processor import process_data
from .signals import detect_golden_crossover, detect_death_cross
from .database import init_db, get_engine, save_daily_metrics, save_signal_events

logger = logging.getLogger("financial_analyzer")


def setup_logging(cfg):
    level = cfg["logging"].get("level", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        force=True,
    )


@click.command()
@click.option("--ticker", "-t", required=True, help="Ticker symbol (e.g. RELIANCE.NS)")
@click.option("--output", "-o", default="analysis.json", help="Output JSON filename")
@click.option("--initdb/--no-initdb", default=True, help="Initialize database")
def run(ticker: str, output: str, initdb: bool):
    """
    Run the full pipeline for a single ticker and save JSON output.
    """
    cfg = load_config()
    setup_logging(cfg)
    logger.info("Starting pipeline for %s", ticker)

    if initdb:
        engine = get_engine()
        init_db(engine)
        logger.info("Database initialized")

    raw = fetch_stock_data(ticker)
    processed = process_data(raw)

    processed = processed.assign(
        date=pd.to_datetime(processed["date"]).dt.tz_localize(None)
    )

    golden_dates = detect_golden_crossover(processed)
    death_dates = detect_death_cross(processed.assign(date=pd.to_datetime(processed["date"])))

    # Prepare signal events
    events = []
    for d in golden_dates:
        events.append({"date": d, "signal_type": "golden_cross", "meta": {}})
    for d in death_dates:
        events.append({"date": d, "signal_type": "death_cross", "meta": {}})

    # Save to DB
    engine = get_engine()
    save_daily_metrics(processed.assign(date=pd.to_datetime(processed["date"])), engine=engine)
    save_signal_events(ticker, events, engine=engine)

    # Export JSON summary
    payload = {
        "ticker": ticker,
        "generated_at": datetime.utcnow().isoformat(),
        "price_rows_count": int(len(processed)),
        "fundamentals_used": raw.get("source_info", {}).get("used", "unknown"),
        "signals": events,
    }
    with open(output, "w", encoding="utf8") as f:
        json.dump(payload, f, indent=2)

    logger.info("Finished. JSON exported to %s", output)


if __name__ == "__main__":
    run()
