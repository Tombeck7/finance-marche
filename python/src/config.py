"""Configuration centralisée du projet."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{ROOT / 'data' / 'finance_marche.db'}")
SQL_DIR = ROOT / "sql"
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"

DEFAULT_TICKERS = [
    "^GSPC", "^FCHI", "^STOXX50E",
    "AAPL", "MSFT", "BNP.PA", "MC.PA",
    "SPY", "CAC.PA", "EURUSD=X",
]
