"""Export des tables et vues vers CSV pour Power BI (Import mode)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from src.db import init_database

OUT = Path(__file__).resolve().parents[2] / "powerbi" / "data"
OUT.mkdir(parents=True, exist_ok=True)


def export(engine, query: str, filename: str) -> int:
    df = pd.read_sql(query, engine)
    path = OUT / filename
    df.to_csv(path, index=False, encoding="utf-8-sig")  # utf-8-sig = BOM pour Excel/PowerBI FR
    print(f"  [OK] {filename} — {len(df)} lignes -> {path}")
    return len(df)


def main():
    print("=== Export Power BI ===")
    engine = init_database()

    export(engine, "SELECT * FROM vw_dashboard_marche",        "vw_dashboard_marche.csv")
    export(engine, "SELECT * FROM dim_instrument",              "dim_instrument.csv")
    export(engine, "SELECT * FROM fact_prix",                   "fact_prix.csv")
    export(engine, "SELECT * FROM fact_indicateurs",            "fact_indicateurs.csv")
    export(engine, "SELECT * FROM dim_produit_structure",       "dim_produit_structure.csv")
    export(engine, "SELECT * FROM dim_client",                  "dim_client.csv")
    export(engine, "SELECT * FROM fact_position_client",        "fact_position_client.csv")

    # Table calendrier (pratique pour Power BI)
    dates = pd.date_range(
        pd.read_sql("SELECT MIN(date_cours) FROM fact_prix", engine).iloc[0, 0],
        pd.read_sql("SELECT MAX(date_cours) FROM fact_prix", engine).iloc[0, 0],
        freq="D",
    )
    cal = pd.DataFrame({
        "Date":      dates.strftime("%Y-%m-%d"),
        "Annee":     dates.year,
        "Trimestre": dates.quarter,
        "Mois":      dates.month,
        "NomMois":   dates.strftime("%B"),
        "Semaine":   dates.isocalendar().week.values,
        "JourSemaine": dates.day_name(),
        "EstJourOuvre": (dates.weekday < 5).astype(int),
    })
    path = OUT / "dim_calendrier.csv"
    cal.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  [OK] dim_calendrier.csv — {len(cal)} lignes -> {path}")

    print(f"\nFichiers disponibles dans : {OUT}")
    print("Ouvrez Power BI Desktop -> Obtenir des donnees -> Texte/CSV")


if __name__ == "__main__":
    main()
