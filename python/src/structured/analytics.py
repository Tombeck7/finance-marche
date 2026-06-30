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
            ps.date_emission, ps.date_echeance, ps.devise,
            ps.reference_entity, ps.recovery_rate_pct, ps.credit_spread_bps,
            ps.credit_event, ps.payoff_summary, ps.sales_argument,
            ps.main_risk, ps.next_action
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
                type_produit: str = "", coupon: float = 0.0,
                credit_spread_bps: float | None = None) -> int:
    """Score de risque 0-100 (plus haut = plus risqué)."""
    if type_produit == "cln":
        # Pour un CLN, le risque est le risque crédit : spread > coupon si disponible.
        spread_bonus = min((credit_spread_bps or 0) / 500 * 35, 35)
        coupon_bonus = min(coupon * 3, 30)
        return min(int(12 + spread_bonus + coupon_bonus), 85)
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
        score      = _risk_score(
            statut,
            worst_of,
            vol_sj1,
            type_prod,
            float(p.get("coupon_annuel_pct") or 0),
            float(p.get("credit_spread_bps") or 0),
        )

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
            "point_attention": _point_attention(p.to_dict(), statut, worst_of, dist_ki),
        })

    return pd.DataFrame(rows)


def _point_attention(product: dict, statut: str, worst_of: float | None, dist_ki: float | None) -> str:
    type_prod = str(product.get("type_produit", ""))
    if type_prod == "cln":
        entity = product.get("reference_entity") or product.get("sous_jacent_1")
        spread = product.get("credit_spread_bps")
        return f"Suivre le risque crédit {entity} et le spread indicatif ({spread:.0f} bps)." if _notna(spread) else f"Suivre le risque crédit {entity}."
    if type_prod == "capital_protected":
        return "Mettre en avant la protection du capital, mais expliquer le risque d’opportunité."
    if statut in ("DANGER", "KI_DECLENCHE"):
        return f"Produit à surveiller en priorité : distance KI {dist_ki:.1f}%."
    if worst_of is not None and worst_of < 0:
        return f"Sous-jacent en baisse ({worst_of:.1f}%) : préparer un argument de suivi."
    return "Produit en zone normale : suivi standard et prochaine observation."


def suitability_score(profile: str, product_type: str, risk_score: int, maturity_days: int | None) -> tuple[int, str]:
    """Score d'adéquation client-produit simple pour usage sales."""
    profile = str(profile).lower()
    type_penalty = {
        "conservateur": {"capital_protected": 0, "cln": 12, "autocall": 25, "reverse_convertible": 30},
        "equilibre": {"capital_protected": 0, "cln": 8, "autocall": 10, "reverse_convertible": 15},
        "dynamique": {"capital_protected": 5, "cln": 0, "autocall": 0, "reverse_convertible": 5},
    }.get(profile, {})
    penalty = type_penalty.get(product_type, 15)
    maturity_penalty = 0 if not maturity_days else min(max((maturity_days - 365) / 365 * 6, 0), 12)
    score = max(0, min(100, int(100 - risk_score - penalty - maturity_penalty)))
    if score >= 70:
        label = "Adapté"
    elif score >= 45:
        label = "À discuter"
    else:
        label = "À éviter"
    return score, label


def profile_label(profile: str) -> str:
    return {
        "conservateur": "conservateur",
        "equilibre": "équilibré",
        "dynamique": "dynamique",
    }.get(str(profile).lower(), str(profile))


def generate_sales_pitch(client: dict | pd.Series, product: dict | pd.Series) -> str:
    """Génère un pitch commercial court et structuré."""
    c = client.to_dict() if hasattr(client, "to_dict") else dict(client)
    p = product.to_dict() if hasattr(product, "to_dict") else dict(product)
    score, label = suitability_score(
        c.get("profil", "equilibre"),
        p.get("type_produit", ""),
        int(float(p.get("score_risque") or 0)),
        int(float(p.get("jours_restants") or 0)) if p.get("jours_restants") is not None else None,
    )
    name = c.get("client") or f"{c.get('nom', '')} {c.get('prenom', '')}".strip() or "ce client"
    product_name = p.get("nom") or p.get("produit") or "ce produit"
    coupon = float(p.get("coupon_annuel_pct") or 0)
    payoff = p.get("payoff_summary") or "Le produit offre une exposition structurée avec un couple rendement/risque défini."
    risk = p.get("main_risk") or p.get("point_attention") or "Le principal risque doit être expliqué avant souscription."
    action = p.get("next_action") or "Vérifier l’adéquation finale avec le profil et les objectifs du client."
    return (
        f"Pour {name}, profil {profile_label(c.get('profil', 'equilibre'))}, "
        f"{product_name} est classé '{label}' avec un score d’adéquation de {score}/100. "
        f"Le produit propose un coupon indicatif de {coupon:.1f}%/an. {payoff} "
        f"Point de vigilance : {risk} Action recommandée : {action}"
    )


def stress_test_product(product: dict | pd.Series) -> pd.DataFrame:
    """Stress tests simples sur le sous-jacent principal."""
    p = product.to_dict() if hasattr(product, "to_dict") else dict(product)
    base_perf = float(p.get("perf_sj1_pct") or 0)
    ki = float(p.get("barriere_ki_pct") or 0)
    rappel = float(p.get("barriere_rappel_pct") or 1)
    coupon = float(p.get("coupon_annuel_pct") or 0)
    ptype = str(p.get("type_produit", ""))
    rows = []
    for shock in [-30, -20, -10, 10]:
        stressed_perf = base_perf + shock
        level = 1 + stressed_perf / 100
        if ptype == "cln":
            statut = "Crédit inchangé"
            resultat = f"Coupon {coupon:.1f}% conservé si aucun événement de crédit."
            perte = 0.0
        elif ptype == "capital_protected":
            statut = "Capital protégé"
            resultat = "Capital protégé à échéance ; risque d’opportunité."
            perte = 0.0
        elif level <= ki:
            statut = "KI touché"
            perte = min((level - 1) * 100, 0)
            resultat = f"Risque de perte indicative {perte:.1f}% à maturité."
        elif level >= rappel:
            statut = "Rappel possible"
            perte = 0.0
            resultat = f"Rappel/coupon possible si observation à ce niveau ({coupon:.1f}%/an)."
        else:
            statut = "Zone intermédiaire"
            perte = 0.0
            resultat = "Pas de rappel immédiat, barrière non touchée."
        rows.append({
            "scenario": f"{shock:+.0f}%",
            "perf_stressee_pct": round(stressed_perf, 1),
            "niveau_pct_strike": round(level * 100, 1),
            "statut": statut,
            "perte_indicative_pct": round(perte, 1),
            "commentaire": resultat,
        })
    return pd.DataFrame(rows)


def build_sales_alerts(
    positions: pd.DataFrame,
    enriched: pd.DataFrame,
    market: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Construit les alertes 'à appeler aujourd'hui'."""
    if positions.empty or enriched.empty:
        return pd.DataFrame(columns=["client", "produit", "priorite", "raison", "action"])
    df = positions.merge(
        enriched[[
            "produit_id", "statut", "score_risque", "dist_barriere_ki_pct",
            "jours_restants", "point_attention", "next_action", "type_produit"
        ]],
        on="produit_id",
        how="left",
        suffixes=("", "_enrich"),
    )
    alerts: list[dict] = []
    for _, r in df.iterrows():
        score = int(float(r.get("score_risque") or 0))
        days = r.get("jours_restants")
        days = int(float(days)) if pd.notna(days) else None
        if r.get("statut") in ("DANGER", "KI_DECLENCHE") or score >= 70:
            alerts.append({
                "client": r["client"], "produit": r["produit"], "priorite": "Haute",
                "raison": r.get("point_attention") or "Produit à risque élevé.",
                "action": r.get("next_action") or "Appeler le client et préparer un point de suivi.",
            })
        if days is not None and 0 < days <= 60:
            alerts.append({
                "client": r["client"], "produit": r["produit"], "priorite": "Moyenne",
                "raison": f"Échéance proche dans {days} jours.",
                "action": "Préparer une idée de réinvestissement.",
            })
    if not df.empty:
        cln = df[df["type_produit"] == "cln"].groupby("client")["nominal_souscrit"].sum()
        total = df.groupby("client")["nominal_souscrit"].sum()
        for client, cln_nominal in cln.items():
            pct = cln_nominal / total.get(client, cln_nominal) * 100
            if pct > 35:
                alerts.append({
                    "client": client, "produit": "Portefeuille CLN", "priorite": "Moyenne",
                    "raison": f"Exposition CLN élevée ({pct:.0f}% de l'encours).",
                    "action": "Éviter d'ajouter du risque crédit et proposer diversification.",
                })
        if market is not None and not market.empty and "date_cours" in market.columns:
            last_market_date = pd.to_datetime(market["date_cours"]).max().date()
            if last_market_date < date.today() - timedelta(days=5):
                for client in sorted(df["client"].dropna().unique()):
                    alerts.append({
                        "client": client,
                        "produit": "Données marché",
                        "priorite": "Moyenne",
                        "raison": f"Données obsolètes : dernière date disponible {last_market_date}.",
                        "action": "Vérifier la source de marché avant d'appeler le client.",
                    })
    return pd.DataFrame(alerts).drop_duplicates() if alerts else pd.DataFrame(
        columns=["client", "produit", "priorite", "raison", "action"]
    )


def barrier_monitor_series(
    product: dict | pd.Series,
    market: pd.DataFrame,
    lookback_days: int = 180,
) -> pd.DataFrame:
    """Série prix sous-jacent vs strike et barrières (niveau % du strike = 100)."""
    p = product.to_dict() if hasattr(product, "to_dict") else dict(product)
    ticker = p.get("sous_jacent_1")
    strike = float(p.get("strike_1") or 1)
    if not ticker or strike <= 0 or market.empty:
        return pd.DataFrame()

    grp = market[market["ticker"] == ticker].sort_values("date_cours").copy()
    if grp.empty:
        return pd.DataFrame()

    cutoff = pd.Timestamp.today() - pd.Timedelta(days=lookback_days)
    grp = grp[grp["date_cours"] >= cutoff]
    if grp.empty:
        return pd.DataFrame()

    ki_pct = float(p.get("barriere_ki_pct") or 0.7)
    rappel_pct = float(p.get("barriere_rappel_pct") or 1.0)
    grp["level_pct"] = grp["close"] / strike * 100
    grp["ki_pct"] = ki_pct * 100
    grp["rappel_pct"] = rappel_pct * 100
    grp["strike_pct"] = 100.0
    return grp[["date_cours", "level_pct", "ki_pct", "rappel_pct", "strike_pct", "close"]].reset_index(drop=True)


def upcoming_observations(
    enriched: pd.DataFrame,
    days_ahead: int = 30,
) -> pd.DataFrame:
    """Produits avec une observation dans les N prochains jours."""
    if enriched.empty:
        return pd.DataFrame(columns=["nom", "type_produit", "sous_jacent_1", "date_obs", "jours"])
    today = date.today()
    rows: list[dict] = []
    for _, p in enriched.iterrows():
        if str(p.get("type_produit", "")) in ("capital_protected", "cln"):
            continue
        d_em = _parse_date(p.get("date_emission"))
        if d_em is None:
            continue
        step_days = {"trimestrielle": 91, "semestrielle": 182, "annuelle": 365}.get(
            str(p.get("periodicite_obs", "trimestrielle")).lower(), 91
        )
        d = d_em
        while d <= today:
            d += timedelta(days=step_days)
        jours = (d - today).days
        if 0 <= jours <= days_ahead:
            rows.append({
                "nom": p.get("nom"),
                "type_produit": p.get("type_produit"),
                "sous_jacent_1": p.get("sous_jacent_1"),
                "date_obs": d.strftime("%Y-%m-%d"),
                "jours": jours,
                "score_risque": int(float(p.get("score_risque") or 0)),
                "dist_barriere_ki_pct": p.get("dist_barriere_ki_pct"),
            })
    if not rows:
        return pd.DataFrame(columns=["nom", "type_produit", "sous_jacent_1", "date_obs", "jours"])
    return pd.DataFrame(rows).sort_values("jours")


def build_meeting_pack_html(
    client: str,
    profil: str,
    segment: str,
    encours: float,
    max_risk: int,
    client_alerts: pd.DataFrame,
    product: dict | pd.Series,
    pitch: str,
) -> str:
    """Génère un HTML autonome imprimable pour le meeting pack."""
    p = product.to_dict() if hasattr(product, "to_dict") else dict(product)
    alert_rows = ""
    if client_alerts.empty:
        alert_rows = "<li>Aucune alerte majeure</li>"
    else:
        for _, a in client_alerts.head(6).iterrows():
            alert_rows += (
                f"<li><strong>{a['priorite']}</strong> — {a['produit']}: "
                f"{a['raison']}</li>"
            )
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8"/>
<title>Meeting Pack — {client}</title>
<style>
body{{font-family:Inter,Segoe UI,sans-serif;background:#fff;color:#1f2937;margin:32px;line-height:1.5;}}
h1{{font-size:24px;margin:0 0 4px;}}
.meta{{color:#6b7280;font-size:13px;margin-bottom:24px;}}
.card{{border:1px solid #e5e7eb;border-radius:10px;padding:16px 18px;margin-bottom:16px;}}
.kpi{{display:inline-block;margin-right:24px;}}
.kpi b{{display:block;font-size:20px;color:#111827;}}
label{{font-size:10px;text-transform:uppercase;color:#6b7280;letter-spacing:.06em;}}
ul{{margin:8px 0;padding-left:20px;}}
.pitch{{background:#f0fdf4;border-left:4px solid #3fb950;padding:12px 14px;border-radius:6px;}}
@media print{{body{{margin:16px;}}}}
</style>
</head>
<body>
<h1>Meeting Pack — {client}</h1>
<div class="meta">Profil {profil} · Segment {segment} · Encours {encours/1000:.0f}k EUR · Risque max {max_risk}/100</div>
<div class="card">
  <label>Alertes à traiter</label>
  <ul>{alert_rows}</ul>
</div>
<div class="card">
  <label>Idée produit</label>
  <h2 style="margin:8px 0 4px;font-size:18px;">{p.get('nom', '')}</h2>
  <div class="kpi"><label>Coupon</label><b>{float(p.get('coupon_annuel_pct') or 0):.1f}%</b></div>
  <div class="kpi"><label>Risque</label><b>{int(float(p.get('score_risque') or 0))}/100</b></div>
  <div class="kpi"><label>Adéquation</label><b>{p.get('adequation', '—')}</b></div>
  <p style="margin-top:12px;">{p.get('payoff_summary', '')}</p>
</div>
<div class="pitch"><strong>Pitch 30 sec</strong><br/>{pitch}</div>
<p style="color:#9ca3af;font-size:11px;margin-top:32px;">Généré par Finance Marché — document indicatif, non contractuel.</p>
</body>
</html>"""


def compare_products(enriched: pd.DataFrame, product_names: list[str] | None = None) -> pd.DataFrame:
    """Prépare une table de comparaison commerciale de 2 à 3 produits."""
    if enriched.empty:
        return pd.DataFrame()
    comp = enriched.copy()
    if product_names:
        comp = comp[comp["nom"].isin(product_names)].copy()
    if comp.empty:
        return pd.DataFrame()

    profile_by_type = {
        "capital_protected": "conservateur",
        "autocall": "équilibré / dynamique",
        "reverse_convertible": "dynamique",
        "cln": "dynamique crédit",
    }
    comp["profil_recommande"] = comp["type_produit"].map(profile_by_type).fillna("à qualifier")
    columns = [
        "nom",
        "type_produit",
        "profil_recommande",
        "sous_jacent_1",
        "coupon_annuel_pct",
        "date_echeance",
        "jours_restants",
        "score_risque",
        "statut",
        "payoff_summary",
        "main_risk",
        "next_action",
    ]
    return comp[[c for c in columns if c in comp.columns]].sort_values(
        ["score_risque", "coupon_annuel_pct"],
        ascending=[True, False],
    )


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
