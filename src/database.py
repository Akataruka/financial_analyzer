# src/database.py
"""
SQLAlchemy-based SQLite persistence with idempotent inserts.
We implement simple ORM classes and helper functions to upsert records.
"""
from __future__ import annotations
from typing import Iterable, List
import sqlalchemy as sa
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy import Column, Integer, String, Float, Date, Text, DateTime
import pandas as pd
from datetime import datetime
import logging
from .config import load_config
import pathlib

logger = logging.getLogger(__name__)
CONFIG = load_config()

Base = declarative_base()


class Ticker(Base):
    __tablename__ = "tickers"
    id = Column(Integer, primary_key=True)
    ticker = Column(String, unique=True, nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    info = Column(Text)


class DailyMetric(Base):
    __tablename__ = "daily_metrics"
    id = Column(Integer, primary_key=True)
    ticker = Column(String, index=True)
    date = Column(Date, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)
    sma50 = Column(Float)
    sma200 = Column(Float)
    price_to_book = Column(Float)
    bvps = Column(Float)
    enterprise_value = Column(Float)

    __table_args__ = (sa.UniqueConstraint("ticker", "date", name="u_ticker_date"),)


class SignalEvent(Base):
    __tablename__ = "signal_events"
    id = Column(Integer, primary_key=True)
    ticker = Column(String, index=True)
    date = Column(Date, index=True)
    signal_type = Column(String)
    meta = Column(Text)

    __table_args__ = (sa.UniqueConstraint("ticker", "date", "signal_type", name="u_signal_unique"),)


def get_engine(db_path: str | None = None):
    if db_path is None:
        db_path = CONFIG["database"]["path"]
    db_url = f"sqlite:///{pathlib.Path(db_path).expanduser().as_posix()}"
    engine = sa.create_engine(db_url, echo=False, future=True)
    return engine


def init_db(engine=None):
    engine = engine or get_engine()
    Base.metadata.create_all(engine)


def save_daily_metrics(df: pd.DataFrame, engine=None):
    """
    Save DataFrame (processed metrics) to daily_metrics table.
    Uses INSERT OR REPLACE semantics to be idempotent.
    """
    engine = engine or get_engine()
    conn = engine.connect()
    # Ensure date format
    df2 = df.copy()
    if "date" in df2.columns:
        df2["date"] = pd.to_datetime(df2["date"]).dt.date
    # Select subset of columns matching DailyMetric model
    cols = ["ticker", "date", "open", "high", "low", "close", "volume", "sma50", "sma200", "price_to_book", "bvps", "enterprise_value"]
    cols = [c for c in cols if c in df2.columns]
    df2 = df2[cols]
    # Use SQLAlchemy core to execute many INSERT OR REPLACE statements
    metadata = Base.metadata
    dm = metadata.tables["daily_metrics"]
    # Convert DataFrame rows to dictionaries
    records = df2.to_dict(orient="records")
    if not records:
        return
    # Build insert statement with OR REPLACE (SQLite) — SQLAlchemy doesn't provide direct OR REPLACE,
    # so we emit raw SQL.
    with conn.begin() as trans:
        for r in records:
            # Prepare values with None-handling
            cols_names = ", ".join(f'"{k}"' for k in r.keys())
            placeholders = ", ".join(f":{k}" for k in r.keys())  # named placeholders

            sql = f'INSERT OR REPLACE INTO daily_metrics ({cols_names}) VALUES ({placeholders})'
            conn.execute(sa.text(sql), r)  # pass dict, not list
        # No need to call trans.commit(), context manager handles it



def save_signal_events(ticker: str, events: Iterable[dict], engine=None):
    """
    events: iterable of dicts with keys: date (ISO), signal_type, meta (optional)
    Use INSERT OR REPLACE to be idempotent.
    """
    engine = engine or get_engine()
    conn = engine.connect()
    with conn.begin() as trans:
        for ev in events:
            d = ev.get("date")
            ttype = ev.get("signal_type")
            meta = ev.get("meta")
            sql = 'INSERT OR REPLACE INTO signal_events (ticker, date, signal_type, meta) VALUES (:ticker, :date, :signal_type, :meta)'
            conn.execute(sa.text(sql), {"ticker": ticker, "date": d, "signal_type": ttype, "meta": str(meta)})
        trans.commit()
