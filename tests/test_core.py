from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from src.db import init_database
from src.ingest.generate_demo_data import generate_demo_data
from src.load_to_sql import load_prices
from src.structured.analytics import (
    barrier_monitor_series,
    build_meeting_pack_html,
    build_sales_alerts,
    compare_products,
    enrich_products_with_market,
    generate_sales_pitch,
    load_positions,
    load_products,
    stress_test_product,
    suitability_score,
    upcoming_observations,
)


def test_products_are_enriched_with_cln_fields():
    engine = init_database()
    load_prices(engine, generate_demo_data(days=120))
    with engine.connect() as conn:
        market = pd.read_sql("SELECT * FROM vw_dashboard_marche", conn)
    market["date_cours"] = pd.to_datetime(market["date_cours"])

    products = load_products(engine)
    enriched = enrich_products_with_market(products, market)

    assert "cln" in set(enriched["type_produit"])
    cln = enriched[enriched["type_produit"] == "cln"].iloc[0]
    assert pd.isna(cln["dist_barriere_ki_pct"])
    assert cln["score_risque"] > 0
    assert "crédit" in cln["point_attention"].lower()


def test_suitability_respects_client_profiles():
    conservative_autocall, conservative_label = suitability_score(
        "conservateur", "autocall", 60, 900
    )
    dynamic_autocall, dynamic_label = suitability_score(
        "dynamique", "autocall", 60, 900
    )

    assert dynamic_autocall > conservative_autocall
    assert conservative_label in {"À discuter", "À éviter"}
    assert dynamic_label in {"Adapté", "À discuter", "À éviter"}


def test_pitch_stress_and_alerts_are_generated():
    engine = init_database()
    load_prices(engine, generate_demo_data(days=120))
    with engine.connect() as conn:
        market = pd.read_sql("SELECT * FROM vw_dashboard_marche", conn)
    market["date_cours"] = pd.to_datetime(market["date_cours"])

    enriched = enrich_products_with_market(load_products(engine), market)
    product = enriched.iloc[0]
    pitch = generate_sales_pitch({"client": "Client Test", "profil": "equilibre"}, product)
    stress = stress_test_product(product)
    stale_market = market.copy()
    stale_market["date_cours"] = stale_market["date_cours"] - pd.Timedelta(days=10)
    alerts = build_sales_alerts(load_positions(engine), enriched, stale_market)

    assert "Client Test" in pitch
    assert "coupon" in pitch.lower()
    assert set(stress["scenario"]) == {"-30%", "-20%", "-10%", "+10%"}
    assert {"client", "produit", "priorite", "raison", "action"}.issubset(alerts.columns)
    assert "Données marché" in set(alerts["produit"])


def test_compare_products_returns_sales_columns():
    engine = init_database()
    load_prices(engine, generate_demo_data(days=120))
    with engine.connect() as conn:
        market = pd.read_sql("SELECT * FROM vw_dashboard_marche", conn)
    market["date_cours"] = pd.to_datetime(market["date_cours"])

    enriched = enrich_products_with_market(load_products(engine), market)
    selected = enriched["nom"].head(3).tolist()
    comparison = compare_products(enriched, selected)

    assert len(comparison) == 3
    assert {
        "nom",
        "type_produit",
        "profil_recommande",
        "coupon_annuel_pct",
        "score_risque",
        "payoff_summary",
        "main_risk",
    }.issubset(comparison.columns)


def test_barrier_monitor_and_meeting_pack_html():
    engine = init_database()
    load_prices(engine, generate_demo_data(days=120))
    with engine.connect() as conn:
        market = pd.read_sql("SELECT * FROM vw_dashboard_marche", conn)
    market["date_cours"] = pd.to_datetime(market["date_cours"])

    enriched = enrich_products_with_market(load_products(engine), market)
    autocall = enriched[enriched["type_produit"] == "autocall"].iloc[0]
    series = barrier_monitor_series(autocall, market)
    assert not series.empty
    assert {"date_cours", "level_pct", "ki_pct", "rappel_pct"}.issubset(series.columns)

    obs = upcoming_observations(enriched, days_ahead=365)
    assert "nom" in obs.columns or obs.empty

    html_doc = build_meeting_pack_html(
        "Client Test", "equilibre", "prive", 500_000, 45,
        pd.DataFrame(), autocall, "Pitch test pour le client.",
    )
    assert "Client Test" in html_doc
    assert "Pitch test" in html_doc
    assert html_doc.count("<html") == 1


if __name__ == "__main__":
    test_products_are_enriched_with_cln_fields()
    test_suitability_respects_client_profiles()
    test_pitch_stress_and_alerts_are_generated()
    test_compare_products_returns_sales_columns()
    test_barrier_monitor_and_meeting_pack_html()
    print("Tests OK")
