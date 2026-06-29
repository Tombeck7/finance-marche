"""Connexion et initialisation de la base SQL."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from .config import DATABASE_URL, SQL_DIR


def get_engine() -> Engine:
    return create_engine(DATABASE_URL, echo=False)


def run_sql_file(engine: Engine, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    with engine.begin() as conn:
        for statement in sql.split(";"):
            stmt = statement.strip()
            if stmt:
                conn.execute(text(stmt))


def init_database(engine: Engine | None = None) -> Engine:
    engine = engine or get_engine()
    run_sql_file(engine, SQL_DIR / "schema" / "01_create_tables.sql")
    run_sql_file(engine, SQL_DIR / "seed" / "seed_instruments.sql")
    run_sql_file(engine, SQL_DIR / "schema" / "02_views.sql")
    run_sql_file(engine, SQL_DIR / "schema" / "03_structured_products.sql")
    run_sql_file(engine, SQL_DIR / "seed" / "seed_structured_products.sql")
    return engine
