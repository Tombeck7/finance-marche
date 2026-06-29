"""Pipeline complet : init DB → téléchargement (Yahoo ou synthétique) → SQL."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db import init_database
from src.load_to_sql import load_prices


def _fetch_yahoo() -> "pd.DataFrame":
    import pandas as pd
    from src.ingest.fetch_yfinance import fetch_market_data

    print("  Tentative Yahoo Finance...")
    try:
        df = fetch_market_data(period="2y")
        if df.empty:
            raise ValueError("Aucune donnée retournée")
        print(f"  [OK] Yahoo Finance : {len(df)} lignes, {df['ticker'].nunique()} instruments")
        return df
    except Exception as exc:
        print(f"  [ERREUR] Yahoo Finance indisponible ({exc})")
        return pd.DataFrame()


def _fetch_demo() -> "pd.DataFrame":
    from src.ingest.generate_demo_data import generate_demo_data

    print("  Génération de données synthétiques (demo)...")
    df = generate_demo_data(days=500)
    print(f"  [OK] Demo : {len(df)} lignes, {df['ticker'].nunique()} instruments")
    return df


def main(force_demo: bool = False) -> None:
    import pandas as pd

    print("=== Finance de Marché — Pipeline ===")
    print("1. Initialisation de la base de données...")
    engine = init_database()

    print("2. Récupération des données...")
    df: pd.DataFrame = pd.DataFrame()
    if not force_demo:
        df = _fetch_yahoo()
    if df.empty:
        df = _fetch_demo()

    print("3. Chargement en base SQL...")
    count = load_prices(engine, df)
    print(f"  [OK] {count} enregistrements inseres/mis a jour")

    print("\nTerminé. Lancez l'app Streamlit :")
    print("  streamlit run app.py")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="Forcer les données synthétiques")
    args = parser.parse_args()
    main(force_demo=args.demo)
