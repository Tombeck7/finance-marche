"""Configuration centralisée du projet."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def _resolve_db_url() -> str:
    """Retourne l'URL SQLite.
    Sur Streamlit Cloud le dossier projet est en lecture seule → on utilise /tmp.
    En local on utilise data/finance_marche.db.
    """
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url

    local_path = ROOT / "data" / "finance_marche.db"
    try:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        probe = local_path.parent / ".write_probe"
        probe.touch()
        probe.unlink()
        return f"sqlite:///{local_path}"
    except (PermissionError, OSError):
        # Filesystem en lecture seule (Streamlit Cloud) → /tmp
        return "sqlite:////tmp/finance_marche.db"


DATABASE_URL = _resolve_db_url()
SQL_DIR = ROOT / "sql"
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"

DEFAULT_TICKERS = [
    "^GSPC", "^FCHI", "^STOXX50E",
    "AAPL", "MSFT", "BNP.PA", "MC.PA", "TTE.PA",
    "SPY", "CAC.PA", "EURUSD=X",
]
