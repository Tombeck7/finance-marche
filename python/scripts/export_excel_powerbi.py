"""Export vers Excel multi-onglets pour Power BI Service."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from sqlalchemy import create_engine

ROOT   = Path(__file__).resolve().parents[2]
OUT    = ROOT / "powerbi" / "data" / "finance_marche_powerbi.xlsx"
DB     = ROOT / "data" / "finance_marche.db"

engine = create_engine(f"sqlite:///{DB}")

print("=== Export Excel pour Power BI Service ===")

sheets = {
    "Marche":            "SELECT * FROM vw_dashboard_marche",
    "Instruments":       "SELECT * FROM dim_instrument",
    "ProduitStructures": "SELECT * FROM dim_produit_structure WHERE actif=1",
    "Clients":           "SELECT * FROM dim_client WHERE actif=1",
    "Positions": """
        SELECT
            p.position_id, p.date_souscription, p.nominal_souscrit,
            c.client_id,
            c.nom || ' ' || COALESCE(c.prenom,'') AS client_nom,
            c.profil, c.segment,
            ps.produit_id,
            ps.nom           AS produit_nom,
            ps.type_produit,
            ps.sous_jacent_1,
            ps.coupon_annuel_pct,
            ps.barriere_ki_pct,
            ps.barriere_rappel_pct,
            ps.date_emission,
            ps.date_echeance
        FROM fact_position_client p
        JOIN dim_client c             ON c.client_id  = p.client_id
        JOIN dim_produit_structure ps ON ps.produit_id = p.produit_id
    """,
}

with pd.ExcelWriter(OUT, engine="openpyxl") as writer:
    for sheet_name, query in sheets.items():
        df = pd.read_sql(query, engine)
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        print(f"  [OK] Onglet '{sheet_name}' : {len(df)} lignes")

print(f"\nFichier cree : {OUT}")
print("Prochaine etape : importer ce fichier dans Power BI Service")
