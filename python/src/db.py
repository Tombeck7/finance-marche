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


def sync_product_instruments(engine: Engine) -> None:
    """Ajoute au référentiel marché les sous-jacents présents dans le book produits."""
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT OR IGNORE INTO dim_instrument (ticker, nom, type_instrument, secteur, devise)
            SELECT DISTINCT ticker, ticker, 'action', 'Sous-jacent produit', 'EUR'
            FROM (
                SELECT sous_jacent_1 AS ticker FROM dim_produit_structure
                UNION
                SELECT sous_jacent_2 AS ticker FROM dim_produit_structure
                UNION
                SELECT sous_jacent_3 AS ticker FROM dim_produit_structure
            )
            WHERE ticker IS NOT NULL AND ticker <> ''
        """))


def init_database(engine: Engine | None = None) -> Engine:
    engine = engine or get_engine()
    run_sql_file(engine, SQL_DIR / "schema" / "01_create_tables.sql")
    run_sql_file(engine, SQL_DIR / "seed" / "seed_instruments.sql")
    run_sql_file(engine, SQL_DIR / "schema" / "02_views.sql")
    run_sql_file(engine, SQL_DIR / "schema" / "03_structured_products.sql")
    run_sql_file(engine, SQL_DIR / "seed" / "seed_structured_products.sql")
    sync_product_instruments(engine)
    return engine
