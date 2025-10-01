# src/config.py
"""
Configuration loader for the financial analyzer.
Reads YAML config (config.yaml).
"""
from __future__ import annotations
import pathlib
import yaml
from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)

DEFAULTS: Dict[str, Any] = {
    "database": {"path": "financial_data.db"},
    "logging": {"level": "INFO"},
    "data_settings": {"historical_period": "5y", "min_trading_days_for_sma": 200},
}


def load_config(path: str | pathlib.Path = "config.yaml") -> Dict[str, Any]:
    """Load YAML config and merge with defaults."""
    p = pathlib.Path(path)
    if not p.exists():
        logger.warning("Config file %s not found, using defaults.", p)
        return DEFAULTS
    with p.open("r", encoding="utf8") as f:
        cfg = yaml.safe_load(f) or {}
    # shallow merge
    merged = {**DEFAULTS, **cfg}
    # ensure nested dicts exist
    merged["database"] = {**DEFAULTS["database"], **cfg.get("database", {})}
    merged["logging"] = {**DEFAULTS["logging"], **cfg.get("logging", {})}
    merged["data_settings"] = {**DEFAULTS["data_settings"], **cfg.get("data_settings", {})}
    return merged
