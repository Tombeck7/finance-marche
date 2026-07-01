"""Imports métier pour clients et positions produits structurés."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine


REQUIRED_POSITION_COLUMNS = {
    "nom",
    "produit_id",
    "date_souscription",
    "nominal_souscrit",
}


@dataclass
class ImportResult:
    rows: int = 0
    clients_created: int = 0
    positions_upserted: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    cleaned.columns = [
        str(c)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        for c in cleaned.columns
    ]
    return cleaned


def _is_blank(value) -> bool:
    if value is None:
        return True
    try:
        return bool(math.isnan(float(value)))
    except (TypeError, ValueError):
        return str(value).strip() == ""


def _value(row: pd.Series, key: str, default: str = ""):
    value = row.get(key, default)
    return default if _is_blank(value) else value


def _product_id_from_row(conn, row: pd.Series) -> int | None:
    if not _is_blank(row.get("produit_id")):
        return int(float(row["produit_id"]))
    if not _is_blank(row.get("isin")):
        found = conn.execute(
            text("SELECT produit_id FROM dim_produit_structure WHERE isin = :isin"),
            {"isin": str(row["isin"]).strip()},
        ).scalar()
        return int(found) if found else None
    if not _is_blank(row.get("produit")):
        found = conn.execute(
            text("SELECT produit_id FROM dim_produit_structure WHERE lower(nom) = lower(:nom)"),
            {"nom": str(row["produit"]).strip()},
        ).scalar()
        return int(found) if found else None
    return None


def _client_id(conn, row: pd.Series) -> tuple[int | None, bool]:
    nom = str(_value(row, "nom")).strip()
    prenom = str(_value(row, "prenom")).strip()
    if not nom:
        return None, False

    found = conn.execute(
        text("""
            SELECT client_id
            FROM dim_client
            WHERE lower(nom) = lower(:nom)
              AND lower(COALESCE(prenom, '')) = lower(:prenom)
            LIMIT 1
        """),
        {"nom": nom, "prenom": prenom},
    ).scalar()
    if found:
        return int(found), False

    profil = str(_value(row, "profil", "equilibre")).strip().lower()
    if profil not in {"conservateur", "equilibre", "dynamique"}:
        profil = "equilibre"
    segment = str(_value(row, "segment", "retail")).strip().lower()
    if segment not in {"retail", "wealth", "institutionnel"}:
        segment = "retail"

    result = conn.execute(
        text("""
            INSERT INTO dim_client (nom, prenom, profil, segment, actif)
            VALUES (:nom, :prenom, :profil, :segment, 1)
        """),
        {"nom": nom, "prenom": prenom or None, "profil": profil, "segment": segment},
    )
    return int(result.lastrowid), True


def import_client_positions(engine: Engine, raw_df: pd.DataFrame) -> ImportResult:
    """Importe un CSV clients/positions.

    Colonnes acceptées :
    - client : `nom`, optionnels `prenom`, `profil`, `segment`
    - produit : `produit_id` ou `isin` ou `produit`
    - position : `date_souscription`, `nominal_souscrit`, optionnel `prix_souscription`
    """
    df = _clean_columns(raw_df)
    result = ImportResult(rows=int(len(df)))
    missing = REQUIRED_POSITION_COLUMNS - set(df.columns)
    if "produit_id" in missing and ({"isin", "produit"} & set(df.columns)):
        missing.remove("produit_id")
    if missing:
        result.errors.append(f"Colonnes manquantes: {', '.join(sorted(missing))}")
        return result

    with engine.begin() as conn:
        for idx, row in df.iterrows():
            line = int(idx) + 2
            try:
                client_id, created = _client_id(conn, row)
                if client_id is None:
                    result.errors.append(f"Ligne {line}: nom client manquant.")
                    continue

                produit_id = _product_id_from_row(conn, row)
                if produit_id is None:
                    result.errors.append(f"Ligne {line}: produit introuvable.")
                    continue

                nominal = float(str(row["nominal_souscrit"]).replace(" ", "").replace(",", "."))
                date_sous = str(row["date_souscription"]).strip()
                prix = float(str(_value(row, "prix_souscription", 100)).replace(",", "."))

                conn.execute(
                    text("""
                        INSERT INTO fact_position_client
                            (client_id, produit_id, date_souscription, nominal_souscrit, prix_souscription)
                        VALUES
                            (:client_id, :produit_id, :date_souscription, :nominal_souscrit, :prix_souscription)
                        ON CONFLICT(client_id, produit_id) DO UPDATE SET
                            date_souscription = excluded.date_souscription,
                            nominal_souscrit = excluded.nominal_souscrit,
                            prix_souscription = excluded.prix_souscription
                    """),
                    {
                        "client_id": client_id,
                        "produit_id": produit_id,
                        "date_souscription": date_sous,
                        "nominal_souscrit": nominal,
                        "prix_souscription": prix,
                    },
                )
                result.positions_upserted += 1
                if created:
                    result.clients_created += 1
            except Exception as exc:
                result.errors.append(f"Ligne {line}: {exc}")

    return result


def sample_client_positions_csv() -> bytes:
    df = pd.DataFrame([
        {
            "nom": "Durand",
            "prenom": "Alice",
            "profil": "equilibre",
            "segment": "wealth",
            "produit_id": 1,
            "date_souscription": "2026-07-01",
            "nominal_souscrit": 150000,
            "prix_souscription": 100,
        },
        {
            "nom": "Durand",
            "prenom": "Alice",
            "profil": "equilibre",
            "segment": "wealth",
            "isin": "XS001000007",
            "date_souscription": "2026-07-01",
            "nominal_souscrit": 50000,
            "prix_souscription": 100,
        },
    ])
    return df.to_csv(index=False).encode("utf-8-sig")
