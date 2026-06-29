"""Calculs analytiques pour produits structurés."""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine


# ── Helpers ───────────────────────────────────────────────────────────────────
def _notna(v) -> bool:
    if v is None:
        return False
    try:
        return not math.isnan(float(v))
    except (TypeError, ValueError):
        return bool(v)


def _parse_date(s) -> date | None:
    try:
        return datetime.strptime(str(s), "%Y-%m-%d").date()
    except Exception:
        return None


# ── Loaders ───────────────────────────────────────────────────────────────────
def load_products(engine: Engine) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql("SELECT * FROM dim_produit_structure WHERE actif=1", conn)


def load_clients(engine: Engine) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql("SELECT * FROM dim_client WHERE actif=1", conn)


def load_positions(engine: Engine) -> pd.DataFrame:
    with engine.connect() as conn:
        q = """
        SELECT
            p.position_id, p.date_souscription, p.nominal_souscrit,
            c.client_id, c.nom || ' ' || COALESCE(c.prenom,'') AS client,
            c.profil, c.segment,
            ps.produit_id, ps.nom AS produit, ps.type_produit,
            ps.sous_jacent_1, ps.sous_jacent_2, ps.sous_jacent_3,
            ps.strike_1, ps.strike_2, ps.strike_3,
            ps.barriere_ki_pct, ps.barriere_rappel_pct, ps.coupon_annuel_pct,
            ps.date_emission, ps.date_echeance, ps.devise
        FROM fact_position_client p
        JOIN dim_client c  ON c.client_id  = p.client_id
        JOIN dim_produit_structure ps ON ps.produit_id = p.produit_id
        """
        return pd.read_sql(q, conn)


# ── Calculs produit ───────────────────────────────────────────────────────────
def _next_obs_date(date_emission: str, periodicite: str) -> str:
    """Calcule la prochaine date d'observation après aujourd'hui."""
    today = date.today()
    d_em = _parse_date(date_emission)
    if d_em is None:
        return "—"

    step_days = {"trimestrielle": 91, "semestrielle": 182, "annuelle": 365}.get(
        str(periodicite).lower(), 91
    )
    d = d_em
    while d <= today:
        d += timedelta(days=step_days)
    jours = (d - today).days
    return f"{d.strftime('%d/%m/%Y')} ({jours}j)"


def _coupon_accumule(date_emission: str, coupon_annuel: float, date_echeance: str) -> float:
    """Coupon théoriquement accumulé depuis l'émission (%)."""
    d_em = _parse_date(date_emission)
    d_ec = _parse_date(date_echeance)
    if d_em is None or d_ec is None:
        return 0.0
    today = date.today()
    elapsed_years = max((today - d_em).days / 365, 0)
    return round(coupon_annuel * elapsed_years, 2)


def _duree_ecoulee_pct(date_emission: str, date_echeance: str) -> float:
    """Pourcentage de la durée totale écoulée (0-100)."""
    d_em = _parse_date(date_emission)
    d_ec = _parse_date(date_echeance)
    if d_em is None or d_ec is None:
        return 0.0
    total = max((d_ec - d_em).days, 1)
    elapsed = max((date.today() - d_em).days, 0)
    return min(round(elapsed / total * 100, 1), 100.0)


def _risk_score(statut: str, worst_of: float | None, vol_ann: float | None,
                type_produit: str = "", coupon: float = 0.0) -> int:
    """Score de risque 0-100 (plus haut = plus risqué)."""
    if type_produit == "cln":
        # Pour un CLN, le risque est le risque de crédit proxié par le coupon
        # Coupon élevé = spread élevé = risque crédit élevé
        return min(int(10 + coupon * 4), 85)
    base      = {"KI_DECLENCHE": 90, "DANGER": 70, "VIGILANCE": 45, "OK": 15, "N/A": 0}.get(statut, 0)
    vol_bonus = min((vol_ann or 0) / 50 * 20, 20)
    wof_bonus = max(0, -((worst_of or 0) / 100) * 10)
    return min(int(base + vol_bonus + wof_bonus), 100)


# ── Enrichissement marché ─────────────────────────────────────────────────────
def enrich_products_with_market(
    products: pd.DataFrame,
    market: pd.DataFrame,
) -> pd.DataFrame:
    last_prices = (
        market.sort_values("date_cours").groupby("ticker")["close"].last().to_dict()
    )
    if "volatilite_20j" in market.columns:
        last_vol = (
            market.sort_values("date_cours")
            .groupby("ticker")["volatilite_20j"]
            .last()
            .to_dict()
        )
    else:
        last_vol = {}

    rows = []
    for _, p in products.iterrows():
        sj1 = p["sous_jacent_1"]
        sj2 = str(p["sous_jacent_2"]) if _notna(p.get("sous_jacent_2")) else None
        sj3 = str(p["sous_jacent_3"]) if _notna(p.get("sous_jacent_3")) else None

        cours1 = last_prices.get(sj1)
        cours2 = last_prices.get(sj2) if sj2 else None
        cours3 = last_prices.get(sj3) if sj3 else None

        # Perf vs strike
        perf1 = (cours1 / p["strike_1"] - 1) * 100 if cours1 else None
        perf2 = (cours2 / p["strike_2"] - 1) * 100 if cours2 and _notna(p.get("strike_2")) else None
        perf3 = (cours3 / p["strike_3"] - 1) * 100 if cours3 and _notna(p.get("strike_3")) else None

        perfs = [v for v in [perf1, perf2, perf3] if v is not None]
        worst_of = min(perfs) if perfs else None

        # Distance barrière KI
        type_prod = str(p.get("type_produit", ""))
        ki = p["barriere_ki_pct"]

        if type_prod in ("capital_protected", "cln"):
            # Pas de barrière KI marchée — risque de crédit pour CLN
            dist_ki = None
            statut  = "OK"
        elif worst_of is not None:
            dist_ki = (worst_of / 100 + 1 - ki) * 100
            if worst_of / 100 + 1 <= ki:
                statut = "KI_DECLENCHE"
            elif dist_ki < 10:
                statut = "DANGER"
            elif dist_ki < 20:
                statut = "VIGILANCE"
            else:
                statut = "OK"
        else:
            dist_ki = None
            statut  = "N/A"

        # Durée restante
        d_ec = _parse_date(p["date_echeance"])
        jours_restants = (d_ec - date.today()).days if d_ec else None

        # Vol principale
        vol_sj1 = (last_vol.get(sj1) or 0) * math.sqrt(252) * 100

        # Données enrichies
        coupon_acc = _coupon_accumule(p["date_emission"], p["coupon_annuel_pct"], p["date_echeance"])
        duree_pct  = _duree_ecoulee_pct(p["date_emission"], p["date_echeance"])
        next_obs   = _next_obs_date(p["date_emission"], p.get("periodicite_obs", "trimestrielle"))
        score      = _risk_score(statut, worst_of, vol_sj1,
                                 type_prod, float(p.get("coupon_annuel_pct") or 0))

        rows.append({
            **p.to_dict(),
            "sj2": sj2,
            "sj3": sj3,
            "cours_actuel_1": cours1,
            "cours_actuel_2": cours2,
            "cours_actuel_3": cours3,
            "perf_sj1_pct":   round(perf1, 2) if perf1 is not None else None,
            "perf_sj2_pct":   round(perf2, 2) if perf2 is not None else None,
            "perf_sj3_pct":   round(perf3, 2) if perf3 is not None else None,
            "worst_of_pct":   round(worst_of, 2) if worst_of is not None else None,
            "dist_barriere_ki_pct": round(dist_ki, 2) if dist_ki is not None else None,
            "jours_restants": jours_restants,
            "statut":         statut,
            "vol_sj1_ann":    round(vol_sj1, 1),
            "coupon_accumule_pct": coupon_acc,
            "duree_ecoulee_pct":   duree_pct,
            "prochaine_observation": next_obs,
            "score_risque":   score,
        })

    return pd.DataFrame(rows)


# ── Simulateur Monte-Carlo ────────────────────────────────────────────────────
def simulate_autocall(
    product: pd.Series,
    nb_scenarios: int = 1000,
    vol_override: float | None = None,
    drift_override: float | None = None,
    market: pd.DataFrame | None = None,
) -> dict:
    ticker  = product["sous_jacent_1"]
    ki_pct  = product["barriere_ki_pct"]
    rappel_pct = product["barriere_rappel_pct"]
    coupon  = product["coupon_annuel_pct"] / 100

    # Paramètres de diffusion depuis l'historique
    if market is not None and ticker in market["ticker"].values:
        grp  = market[market["ticker"] == ticker].sort_values("date_cours")
        rets = grp["rendement_jour"].dropna()
        vol_ann = float(rets.std() * np.sqrt(252)) if vol_override is None else vol_override
        drift   = float(rets.mean() * 252)         if drift_override is None else drift_override
    else:
        vol_ann = vol_override or 0.20
        drift   = drift_override or 0.04

    dt = 1 / 252
    d_ec = _parse_date(product["date_echeance"])
    mat  = max(((d_ec - date.today()).days / 365) if d_ec else 2.0, 0.25)

    nb_steps = int(mat * 252)
    rng = np.random.default_rng(42)
    z   = rng.standard_normal((nb_scenarios, nb_steps))
    log_rets = (drift - 0.5 * vol_ann**2) * dt + vol_ann * np.sqrt(dt) * z
    paths    = np.exp(np.cumsum(log_rets, axis=1))

    # Périodicité
    per = str(product.get("periodicite_obs", "trimestrielle")).lower()
    step_obs = {"trimestrielle": 63, "semestrielle": 126, "annuelle": 252}.get(per, 63)
    obs_steps = list(range(step_obs, nb_steps, step_obs))
    if not obs_steps:
        obs_steps = [nb_steps - 1]

    rappel_count    = np.zeros(len(obs_steps))
    already_recalled= np.zeros(nb_scenarios, dtype=bool)
    ki_triggered    = np.zeros(nb_scenarios, dtype=bool)
    payoffs         = np.full(nb_scenarios, np.nan)

    for i, step in enumerate(obs_steps):
        px = paths[:, step - 1]
        ki_triggered |= (px < ki_pct)
        new_recalled  = (~already_recalled) & (px >= rappel_pct)
        rappel_count[i] = new_recalled.sum()
        t = step / 252
        payoffs[new_recalled] = 1.0 + coupon * t
        already_recalled |= new_recalled

    # Maturité pour non rappelés
    final = paths[:, -1]
    not_recalled = ~already_recalled
    payoffs[not_recalled] = np.where(
        final[not_recalled] >= ki_pct,
        1.0 + coupon * mat,
        final[not_recalled],
    )

    # Distribution des payoffs finaux
    payoff_pct = (payoffs - 1) * 100

    # Scénarios déterministes (bull / base / bear)
    scenarios_det = {}
    for label, drift_s in [("Bull (+30%/an)", 0.30), ("Base (0%/an)", 0.0), ("Bear (-30%/an)", -0.30)]:
        z_s   = rng.standard_normal((200, nb_steps))
        lr_s  = (drift_s - 0.5 * vol_ann**2) * dt + vol_ann * np.sqrt(dt) * z_s
        p_s   = np.exp(np.cumsum(lr_s, axis=1))
        scenarios_det[label] = p_s.mean(axis=0).tolist()

    return {
        "prob_rappel_par_date":   (rappel_count / nb_scenarios * 100).tolist(),
        "obs_dates_labels":       [f"T+{(i+1)*int(step_obs/21)}m" for i in range(len(obs_steps))],
        "prob_ki_pct":            float(ki_triggered.mean() * 100),
        "prob_rappel_total_pct":  float(already_recalled.mean() * 100),
        "rendement_estime_pct":   float(payoff_pct.mean()),
        "rendement_median_pct":   float(np.median(payoff_pct)),
        "perte_max_pct":          float(payoff_pct.min()),
        "vol_utilisee":           vol_ann,
        "scenarios":              nb_scenarios,
        "paths_sample":           paths[:50].tolist(),
        "payoffs_sample":         payoff_pct[:500].tolist(),
        "nb_steps":               nb_steps,
        "mat_years":              mat,
        "ki_pct":                 ki_pct,
        "rappel_pct":             rappel_pct,
        "scenarios_det":          scenarios_det,
    }
