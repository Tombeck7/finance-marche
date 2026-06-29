"""Initialisation des tables et données produits structurés."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

SQL_DIR = Path(__file__).resolve().parents[3] / "sql"


def init_structured_products(engine: Engine) -> None:
    """Crée les tables et insère les données seed."""
    _run_sql(engine, SQL_DIR / "schema" / "03_structured_products.sql")
    _run_sql(engine, SQL_DIR / "seed" / "seed_structured_products.sql")


def _run_sql(engine: Engine, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    with engine.begin() as conn:
        for stmt in sql.split(";"):
            s = stmt.strip()
            if s:
                conn.execute(text(s))
