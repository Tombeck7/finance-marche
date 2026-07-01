"""Pages Streamlit — Produits Structurés (v2)."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .analytics import (
    barrier_monitor_series,
    build_meeting_pack_html,
    build_sales_alerts,
    compare_products,
    enrich_products_with_market,
    generate_sales_pitch,
    load_positions,
    load_products,
    simulate_autocall,
    stress_test_product,
    suitability_score,
    upcoming_observations,
)
from .imports import import_client_positions, sample_client_positions_csv
from src.ui.components import demo_banner, pitch_block

# ── Palette ───────────────────────────────────────────────────────────────────
BG       = "#0d1117"
BG_CARD  = "#161b22"
BG_CARD2 = "#1c2230"
BORDER   = "#30363d"
ACCENT   = "#58a6ff"
GREEN    = "#3fb950"
RED      = "#f85149"
YELLOW   = "#d29922"
PURPLE   = "#bc8cff"
TEXT     = "#e6edf3"
MUTED    = "#8b949e"
CHART_C  = ["#58a6ff","#3fb950","#f78166","#d29922","#bc8cff","#39d353","#ff7b72","#ffa657"]

STATUT_COLOR = {"OK": GREEN, "VIGILANCE": YELLOW, "DANGER": RED, "KI_DECLENCHE": "#c0392b", "N/A": MUTED}
STATUT_LABEL = {"OK": "OK", "VIGILANCE": "Vigilance", "DANGER": "Danger !", "KI_DECLENCHE": "KI déclenché", "N/A": "—"}
TYPE_LABEL   = {
    "autocall":           "Autocall",
    "reverse_convertible":"Rev. Conv.",
    "capital_protected":  "Cap. Protégé",
    "cln":                "CLN",
}


def _rgba(hex_color: str, alpha: float = 0.15) -> str:
    """Convertit un hex #RRGGBB en rgba(r,g,b,alpha) — compatible Plotly."""
    h = hex_color.lstrip("#")
    if len(h) == 6:
        r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
        return f"rgba({r},{g},{b},{alpha})"
    return hex_color


# ── Helpers ───────────────────────────────────────────────────────────────────
def _v(val, default="") -> str:
    if val is None: return default
    try:
        if math.isnan(float(val)): return default
    except (TypeError, ValueError): pass
    return str(val) if str(val) else default

def _ok(val) -> bool:
    return _v(val) != ""

def _f(val, default=0.0) -> float:
    try: return float(val)
    except (TypeError, ValueError): return default


def _chart(fig, height=380, **kw):
    fig.update_layout(
        height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=BG,
        font=dict(family="Inter, Segoe UI, sans-serif", color=MUTED, size=12),
        xaxis=dict(gridcolor=BORDER, zeroline=False, linecolor=BORDER),
        yaxis=dict(gridcolor=BORDER, zeroline=False, linecolor=BORDER),
        margin=dict(l=10, r=10, t=24, b=10),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=BORDER,
                    font=dict(size=11, color=MUTED), orientation="h", y=-0.18),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=BG_CARD2, bordercolor=BORDER, font=dict(color=TEXT, size=12)),
        **kw,
    )
    return fig

def _kpi(label, value, color=TEXT, sub=""):
    sub_html = f'<div style="font-size:11px;color:{MUTED};margin-top:3px;">{sub}</div>' if sub else ""
    st.markdown(f"""
    <div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:10px;padding:16px 18px 12px;">
      <div style="font-size:10px;color:{MUTED};text-transform:uppercase;letter-spacing:.07em;margin-bottom:5px;">{label}</div>
      <div style="font-size:24px;font-weight:700;color:{color};line-height:1.1;">{value}</div>
      {sub_html}
    </div>""", unsafe_allow_html=True)

def _sec(title):
    st.markdown(f'<div style="font-size:11px;font-weight:700;color:{MUTED};text-transform:uppercase;letter-spacing:.1em;margin:22px 0 10px;padding-bottom:6px;border-bottom:1px solid {BORDER};">{title}</div>', unsafe_allow_html=True)

def _badge(statut):
    c  = STATUT_COLOR.get(statut, MUTED)
    lb = STATUT_LABEL.get(statut, statut)
    return f'<span style="background:{c}22;color:{c};border:1px solid {c};border-radius:4px;padding:2px 9px;font-size:11px;font-weight:700;">{lb}</span>'

def _progress_bar(pct: float, statut: str) -> str:
    """Barre de progression HTML pour la distance à la barrière KI."""
    color = STATUT_COLOR.get(statut, MUTED)
    capped = min(max(pct, 0), 100)
    return f"""
    <div style="width:100%;background:#1c2230;border-radius:4px;height:6px;margin-top:5px;overflow:hidden;">
      <div style="width:{capped:.0f}%;background:{color};height:100%;border-radius:4px;
                  transition:width .3s;"></div>
    </div>
    <div style="display:flex;justify-content:space-between;margin-top:2px;">
      <span style="font-size:10px;color:{MUTED};">KI {capped:.0f}%</span>
      <span style="font-size:10px;color:{color};font-weight:600;">{capped:.1f}% restant</span>
    </div>"""

def _header(title: str, sub: str):
    st.markdown(f'<div style="font-size:22px;font-weight:700;color:{TEXT};margin-bottom:3px;">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:13px;color:{MUTED};margin-bottom:20px;">{sub}</div>', unsafe_allow_html=True)


def _download_csv(label: str, df: pd.DataFrame, filename: str):
    st.download_button(
        label,
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name=filename,
        mime="text/csv",
        use_container_width=True,
    )


def _risk_color(score: int) -> str:
    return GREEN if score < 30 else (YELLOW if score < 60 else RED)


def _payoff_profile_fig(row, height: int = 260) -> go.Figure:
    """Profil de payoff indicatif, volontairement simple pour support sales."""
    ptype = str(row.get("type_produit", ""))
    coupon = _f(row.get("coupon_annuel_pct"))
    ki = _f(row.get("barriere_ki_pct"), 0.7) * 100
    rappel = _f(row.get("barriere_rappel_pct"), 1.0) * 100
    levels = np.linspace(50, 130, 81)

    if ptype == "capital_protected":
        payoff = np.maximum(0, (levels - 100) * 0.45)
        title = "Profil indicatif : capital protégé"
    elif ptype == "cln":
        payoff = np.full_like(levels, coupon)
        title = "Profil indicatif : CLN hors événement crédit"
    elif ptype == "reverse_convertible":
        payoff = np.where(levels < ki, coupon + levels - 100, coupon)
        title = "Profil indicatif : reverse convertible"
    else:
        payoff = np.where(levels >= rappel, coupon, np.where(levels <= ki, levels - 100, coupon * 0.35))
        title = "Profil indicatif : autocall"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=levels,
        y=payoff,
        mode="lines",
        line=dict(color=ACCENT, width=3),
        fill="tozeroy",
        fillcolor=_rgba(ACCENT, 0.10),
        name="Payoff indicatif",
    ))
    fig.add_hline(y=0, line_color=BORDER, line_width=1)
    if ptype not in ("capital_protected", "cln"):
        fig.add_vline(x=ki, line_color=RED, line_dash="dash", line_width=1.4,
                      annotation_text=f"KI {ki:.0f}%", annotation_font_color=RED, annotation_font_size=10)
    if ptype == "autocall":
        fig.add_vline(x=rappel, line_color=GREEN, line_dash="dash", line_width=1.4,
                      annotation_text=f"Rappel {rappel:.0f}%", annotation_font_color=GREEN, annotation_font_size=10)
    _chart(fig, height=height)
    fig.update_layout(
        title=dict(text=title, font=dict(color=TEXT, size=13)),
        xaxis_title="Sous-jacent à maturité (% strike)",
        yaxis_title="Payoff indicatif (%)",
        showlegend=False,
    )
    return fig


def _comparator_radar_fig(comp: pd.DataFrame) -> go.Figure:
    categories = ["Coupon", "Protection", "Risque maîtrisé", "Maturité courte", "Simplicité"]
    complexity = {"capital_protected": 75, "reverse_convertible": 55, "autocall": 45, "cln": 35}
    fig = go.Figure()
    for _, row in comp.iterrows():
        score = int(_f(row.get("score_risque")))
        days = max(_f(row.get("jours_restants")), 0)
        values = [
            min(_f(row.get("coupon_annuel_pct")) * 10, 100),
            100 if row.get("type_produit") == "capital_protected" else max(0, 100 - score),
            max(0, 100 - score),
            max(10, 100 - min(days / 730 * 70, 90)),
            complexity.get(row.get("type_produit"), 50),
        ]
        fig.add_trace(go.Scatterpolar(
            r=values + [values[0]],
            theta=categories + [categories[0]],
            fill="toself",
            name=str(row.get("nom", ""))[:28],
        ))
    fig.update_layout(
        height=360,
        paper_bgcolor="rgba(0,0,0,0)",
        polar=dict(
            bgcolor=BG,
            radialaxis=dict(visible=True, range=[0, 100], gridcolor=BORDER, tickfont=dict(color=MUTED, size=9)),
            angularaxis=dict(gridcolor=BORDER, tickfont=dict(color=MUTED, size=10)),
        ),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=MUTED, size=10), orientation="h", y=-0.12),
        margin=dict(l=20, r=20, t=20, b=20),
        font=dict(color=MUTED),
    )
    return fig


_DEMO_STEPS = [
    ("Meeting Pack", "Préparer le rendez-vous : synthèse client, alertes et idée produit."),
    ("Comparateur", "Comparer 2 à 3 idées pour argumenter le choix en rendez-vous."),
    ("Book Produits", "Approfondir payoff, risque et stress tests sur l'idée retenue."),
    ("Dashboard Manager", "Montrer la vue manager : encours, alertes et priorités."),
    ("Meeting Pack", "Exporter le pack HTML et conclure la démo."),
]


def _maybe_demo(page_key: str) -> None:
    if not st.session_state.get("demo_mode"):
        return
    targets = [s[0] for s in _DEMO_STEPS]
    step = int(st.session_state.get("demo_step", 0))
    if page_key == targets[min(step, len(targets) - 1)]:
        demo_banner(step, len(_DEMO_STEPS), _DEMO_STEPS[step][1])
        if step < len(_DEMO_STEPS) - 1:
            if st.button("Étape suivante →", key=f"demo_next_{page_key}"):
                st.session_state["demo_step"] = step + 1
                st.session_state["nav_sel"] = _DEMO_STEPS[step + 1][0]
                st.rerun()


def _barrier_monitor_fig(row, market_df: pd.DataFrame, height: int = 300) -> go.Figure | None:
    series = barrier_monitor_series(row, market_df)
    if series.empty:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=series["date_cours"], y=series["level_pct"],
        name="Sous-jacent (% strike)", mode="lines",
        line=dict(color=ACCENT, width=2),
    ))
    fig.add_hline(y=series["ki_pct"].iloc[0], line_dash="dash", line_color=RED,
                  annotation_text="KI", annotation_font_color=RED, annotation_font_size=10)
    fig.add_hline(y=series["rappel_pct"].iloc[0], line_dash="dash", line_color=GREEN,
                  annotation_text="Rappel", annotation_font_color=GREEN, annotation_font_size=10)
    fig.add_hline(y=100, line_color=MUTED, line_width=1,
                  annotation_text="Strike", annotation_font_color=MUTED, annotation_font_size=10)
    _chart(fig, height=height)
    fig.update_layout(
        showlegend=False,
        yaxis_title="Niveau (% du strike)",
        xaxis_title="",
    )
    return fig


def _sparkline_fig(market_df: pd.DataFrame, ticker: str, color: str = ACCENT) -> go.Figure | None:
    grp = market_df[market_df["ticker"] == ticker].sort_values("date_cours").tail(30)
    if grp.empty:
        return None
    fig = go.Figure(go.Scatter(
        x=grp["date_cours"], y=grp["close"],
        mode="lines", line=dict(color=color, width=1.5),
        fill="tozeroy", fillcolor=_rgba(color, 0.12),
    ))
    fig.update_layout(
        height=60, margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        showlegend=False,
    )
    return fig


def _family_pitch(row) -> tuple[str, str, str]:
    t = row.get("type_produit")
    if t == "cln":
        return (
            "Risque crédit",
            _v(row.get("payoff_summary"), "Coupon conditionné à l’absence d’événement de crédit."),
            _v(row.get("next_action"), "Valider la compréhension du risque de crédit."),
        )
    if t == "capital_protected":
        return (
            "Protection",
            _v(row.get("payoff_summary"), "Capital protégé à échéance avec participation au sous-jacent."),
            _v(row.get("next_action"), "Positionner auprès de profils prudents."),
        )
    if t == "reverse_convertible":
        return (
            "Rendement court terme",
            _v(row.get("payoff_summary"), "Coupon élevé avec risque de livraison du sous-jacent."),
            _v(row.get("next_action"), "Vérifier que le client accepte le sous-jacent en portefeuille."),
        )
    return (
        "Coupon conditionnel",
        _v(row.get("payoff_summary"), "Coupon potentiel et rappel automatique selon le niveau du sous-jacent."),
        _v(row.get("next_action"), "Suivre la prochaine date d’observation."),
    )


# ── PAGE : Suivi Produits ─────────────────────────────────────────────────────
def page_suivi_produits(engine, market_df: pd.DataFrame):
    _header("Suivi Produits Structurés",
            "Monitoring en temps réel des barrières, knock-in et performances")

    products = load_products(engine)
    if products.empty:
        st.warning("Aucun produit.")
        return

    enriched = enrich_products_with_market(products, market_df)

    # ── KPIs ──
    ok  = (enriched["statut"] == "OK").sum()
    vi  = (enriched["statut"] == "VIGILANCE").sum()
    da  = (enriched["statut"] == "DANGER").sum()
    ki  = (enriched["statut"] == "KI_DECLENCHE").sum()
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: _kpi("Total produits", str(len(enriched)))
    with c2: _kpi("OK", str(ok), GREEN)
    with c3: _kpi("Vigilance", str(vi), YELLOW)
    with c4: _kpi("Danger", str(da), RED)
    with c5: _kpi("KI déclenché", str(ki), "#c0392b")

    st.markdown("<br>", unsafe_allow_html=True)
    col_l, col_r = st.columns([3, 2])

    # ── Graphique distances barrière ──
    with col_l:
        _sec("DISTANCE À LA BARRIÈRE KNOCK-IN")
        gd = enriched.dropna(subset=["dist_barriere_ki_pct"]).sort_values("dist_barriere_ki_pct")
        bar_colors = [STATUT_COLOR.get(s, MUTED) for s in gd["statut"]]
        fig = go.Figure(go.Bar(
            x=gd["dist_barriere_ki_pct"],
            y=gd["nom"].str[:32],
            orientation="h",
            marker_color=bar_colors,
            text=gd["dist_barriere_ki_pct"].apply(lambda x: f"{x:.1f}%"),
            textposition="outside",
            textfont=dict(color=TEXT, size=11),
        ))
        fig.add_vline(x=10, line_dash="dash", line_color=RED,    line_width=1.5,
                      annotation_text="Danger",    annotation_font_color=RED,    annotation_font_size=10)
        fig.add_vline(x=20, line_dash="dash", line_color=YELLOW, line_width=1.5,
                      annotation_text="Vigilance", annotation_font_color=YELLOW, annotation_font_size=10)
        h = max(280, len(gd) * 44)
        _chart(fig, height=h)
        fig.update_layout(showlegend=False, xaxis_title="Distance restante (%)")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── Matrice de risque ──
    with col_r:
        _sec("MATRICE RISQUE — VOL × DISTANCE KI")
        mat_df = enriched.dropna(subset=["dist_barriere_ki_pct", "vol_sj1_ann"])
        fig2 = go.Figure()
        for statut, grp in mat_df.groupby("statut"):
            col = STATUT_COLOR.get(statut, MUTED)
            fig2.add_trace(go.Scatter(
                x=grp["dist_barriere_ki_pct"], y=grp["vol_sj1_ann"],
                mode="markers+text",
                text=grp["sous_jacent_1"],
                textposition="top center", textfont=dict(size=9, color=MUTED),
                marker=dict(size=12, color=col, line=dict(color=BG, width=1.5)),
                name=STATUT_LABEL.get(statut, statut),
            ))
        fig2.add_vline(x=10, line_color=RED,    line_dash="dot", line_width=1)
        fig2.add_vline(x=20, line_color=YELLOW, line_dash="dot", line_width=1)
        _chart(fig2, height=h)
        fig2.update_layout(
            xaxis_title="Distance KI (%)", yaxis_title="Volatilité ann. (%)",
            legend=dict(orientation="h", y=-0.22, font=dict(size=10)),
        )
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    # ── Filtres ──
    _sec("FICHES PRODUITS")
    cf1, cf2, cf3 = st.columns([2, 3, 2])
    statut_f = cf1.selectbox("Statut", ["Tous"] + list(STATUT_LABEL.values())[:4])
    type_f   = cf2.multiselect("Type", enriched["type_produit"].unique().tolist(),
                                default=enriched["type_produit"].unique().tolist())
    sort_f   = cf3.selectbox("Trier par", ["Distance KI ↑", "Risque ↓", "Coupon ↓", "Maturité ↑"])

    disp = enriched[enriched["type_produit"].isin(type_f)].copy()
    if statut_f != "Tous":
        inv = {v: k for k, v in STATUT_LABEL.items()}
        disp = disp[disp["statut"] == inv.get(statut_f, statut_f)]

    sort_map = {
        "Distance KI ↑": ("dist_barriere_ki_pct", True),
        "Risque ↓":       ("score_risque", False),
        "Coupon ↓":       ("coupon_annuel_pct", False),
        "Maturité ↑":     ("jours_restants", True),
    }
    col_s, asc = sort_map[sort_f]
    disp = disp.sort_values(col_s, ascending=asc)

    export_cols = [
        "nom", "isin", "type_produit", "sous_jacent_1", "coupon_annuel_pct",
        "date_echeance", "statut", "score_risque", "worst_of_pct",
        "dist_barriere_ki_pct", "payoff_summary", "sales_argument",
        "main_risk", "next_action",
    ]
    _download_csv(
        "Exporter les produits filtrés",
        disp[[c for c in export_cols if c in disp.columns]],
        "produits_structures_filtres.csv",
    )
    risk_export = enriched[(enriched["score_risque"] >= 60) | (enriched["statut"].isin(["DANGER", "KI_DECLENCHE"]))]
    if not risk_export.empty:
        _download_csv(
            "Exporter les produits à risque",
            risk_export[[c for c in export_cols if c in risk_export.columns]],
            "produits_a_risque.csv",
        )

    for _, row in disp.iterrows():
        dist = _f(row.get("dist_barriere_ki_pct"))
        wof  = _f(row.get("worst_of_pct"))
        wof_c = GREEN if wof >= 0 else RED
        score = int(_f(row.get("score_risque")))
        score_c = GREEN if score < 30 else (YELLOW if score < 60 else RED)

        # Sous-jacents multiples
        sjs = row["sous_jacent_1"]
        perfs_html = f'<span style="color:{GREEN if _f(row.get("perf_sj1_pct"))>=0 else RED};font-weight:600;">{_f(row.get("perf_sj1_pct")):+.1f}%</span>'
        if _ok(row.get("sj2")):
            p2c = GREEN if _f(row.get("perf_sj2_pct")) >= 0 else RED
            sjs += f" / {_v(row.get('sj2'))}"
            perfs_html += f' <span style="color:{MUTED};">·</span> <span style="color:{p2c};font-weight:600;">{_f(row.get("perf_sj2_pct")):+.1f}%</span>'
        if _ok(row.get("sj3")):
            p3c = GREEN if _f(row.get("perf_sj3_pct")) >= 0 else RED
            sjs += f" / {_v(row.get('sj3'))}"
            perfs_html += f' <span style="color:{MUTED};">·</span> <span style="color:{p3c};font-weight:600;">{_f(row.get("perf_sj3_pct")):+.1f}%</span>'

        dur_pct = _f(row.get("duree_ecoulee_pct"))
        pitch_title, payoff, action = _family_pitch(row)
        main_risk = _v(row.get("main_risk"), _v(row.get("point_attention"), "Risque à préciser."))
        if row["type_produit"] == "cln":
            barrier_label = "RECOUVREMENT"
            barrier_value = f"{_f(row.get('recovery_rate_pct'), _f(row.get('barriere_ki_pct')) * 100):.0f}%"
        elif row["type_produit"] == "capital_protected":
            barrier_label = "PROTECTION"
            barrier_value = "100%"
        else:
            barrier_label = "DIST. KI"
            barrier_value = f"{dist:.1f}%"

        jr   = _f(row.get("jours_restants"))
        jr_s = f"{int(jr)}j restants" if jr > 0 else _v(row.get("date_echeance",""))
        if row["type_produit"] == "capital_protected":
            ki_html = f'<span style="color:{GREEN};font-size:12px;font-weight:600;">Capital 100% protégé à l\'échéance</span>'
        elif row["type_produit"] == "cln":
            recov = _f(row.get("barriere_ki_pct")) * 100
            ki_html = (
                f'<span style="color:{YELLOW};font-size:12px;font-weight:600;">'
                f'Risque de crédit — taux de recouvrement estimé : {recov:.0f}%</span>'
            )
        else:
            ki_html = _progress_bar(dist, row["statut"])
        st.markdown(f"""
        <div style="background:{BG_CARD};border:1px solid {BORDER};border-left:3px solid {STATUT_COLOR.get(row['statut'],MUTED)};
                    border-radius:10px;padding:16px 20px;margin-bottom:10px;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;">
            <div>
              <span style="font-size:14px;font-weight:700;color:{TEXT};">{row['nom']}</span>
              <span style="font-size:10px;color:{MUTED};margin-left:8px;font-family:monospace;">{_v(row.get('isin'))}</span><br>
              <span style="font-size:11px;color:{MUTED};">{TYPE_LABEL.get(row['type_produit'], row['type_produit'])} · {sjs}</span>
            </div>
            <div style="text-align:right;">
              {_badge(row['statut'])}
              <div style="margin-top:4px;font-size:11px;color:{score_c};">Score risque: {score}/100</div>
              <div style="width:100%;background:#1c2230;border-radius:4px;height:5px;overflow:hidden;">
                <div style="width:{score}%;background:{score_c};height:100%;border-radius:4px;"></div>
              </div>
            </div>
          </div>
          <div style="display:grid;grid-template-columns:repeat(6,1fr);gap:14px;font-size:12px;margin-bottom:12px;">
            <div>
              <div style="color:{MUTED};font-size:10px;margin-bottom:3px;">PERF. SJ(S)</div>
              <div>{perfs_html}</div>
            </div>
            <div>
              <div style="color:{MUTED};font-size:10px;margin-bottom:3px;">WORST-OF</div>
              <div style="color:{wof_c};font-weight:700;">{wof:+.1f}%</div>
            </div>
            <div>
              <div style="color:{MUTED};font-size:10px;margin-bottom:3px;">{barrier_label}</div>
              <div style="color:{STATUT_COLOR.get(row['statut'],MUTED)};font-weight:700;">
                {barrier_value}
              </div>
            </div>
            <div>
              <div style="color:{MUTED};font-size:10px;margin-bottom:3px;">COUPON /AN</div>
              <div style="color:{ACCENT};font-weight:700;">{row['coupon_annuel_pct']:.1f}%</div>
            </div>
            <div>
              <div style="color:{MUTED};font-size:10px;margin-bottom:3px;">COUPON ACC.</div>
              <div style="color:{ACCENT};font-weight:600;">{_f(row.get('coupon_accumule_pct')):.1f}%</div>
            </div>
            <div>
              <div style="color:{MUTED};font-size:10px;margin-bottom:3px;">PROCH. OBS.</div>
              <div style="color:{TEXT};font-size:11px;">{_v(row.get('prochaine_observation'),'—')}</div>
            </div>
          </div>
          <div style="margin-bottom:8px;">
            <div style="font-size:10px;color:{MUTED};margin-bottom:3px;">{"RISQUE CRÉDIT" if row["type_produit"]=="cln" else "DISTANCE À LA BARRIÈRE KNOCK-IN"}</div>
            {ki_html}
          </div>
          <div style="display:grid;grid-template-columns:1.2fr 1.2fr 1fr;gap:10px;margin:10px 0 8px;font-size:11px;">
            <div style="background:{BG_CARD2};border:1px solid {BORDER};border-radius:6px;padding:9px 10px;">
              <div style="color:{ACCENT};font-weight:700;font-size:10px;text-transform:uppercase;margin-bottom:4px;">{pitch_title}</div>
              <div style="color:{TEXT};line-height:1.35;">{payoff}</div>
            </div>
            <div style="background:{BG_CARD2};border:1px solid {BORDER};border-radius:6px;padding:9px 10px;">
              <div style="color:{YELLOW};font-weight:700;font-size:10px;text-transform:uppercase;margin-bottom:4px;">Risque principal</div>
              <div style="color:{TEXT};line-height:1.35;">{main_risk}</div>
            </div>
            <div style="background:{BG_CARD2};border:1px solid {BORDER};border-radius:6px;padding:9px 10px;">
              <div style="color:{GREEN};font-weight:700;font-size:10px;text-transform:uppercase;margin-bottom:4px;">Action sales</div>
              <div style="color:{TEXT};line-height:1.35;">{action}</div>
            </div>
          </div>
          <div>
            <div style="font-size:10px;color:{MUTED};margin-bottom:3px;">DURÉE ÉCOULÉE</div>
            <div style="width:100%;background:#1c2230;border-radius:4px;height:4px;overflow:hidden;">
              <div style="width:{dur_pct:.0f}%;background:{MUTED};height:100%;border-radius:4px;"></div>
            </div>
            <div style="display:flex;justify-content:space-between;margin-top:2px;">
              <span style="font-size:10px;color:{MUTED};">{_v(row.get('date_emission'),'')}</span>
              <span style="font-size:10px;color:{MUTED};">{jr_s}</span>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        if str(row.get("type_produit", "")) not in ("capital_protected", "cln"):
            bfig = _barrier_monitor_fig(row, market_df, height=240)
            if bfig:
                st.plotly_chart(bfig, use_container_width=True, config={"displayModeBar": False})


# ── PAGE : Simulateur Autocall ────────────────────────────────────────────────
def page_simulateur(engine, market_df: pd.DataFrame):
    _header("Simulateur Autocall — Monte-Carlo",
            "Analyse probabiliste des scénarios, payoff et trajectoires")

    products  = load_products(engine)
    autocalls = products[products["type_produit"].isin(["autocall", "reverse_convertible"])]
    if autocalls.empty:
        st.warning("Aucun autocall trouvé.")
        return

    # ── Paramètres ──
    cf1, cf2, cf3, cf4 = st.columns([3, 1, 1, 1])
    prod_sel = cf1.selectbox("Produit", autocalls["nom"].tolist())
    product  = autocalls[autocalls["nom"] == prod_sel].iloc[0]
    vol_pct  = cf2.number_input("Volatilité (%)", 5, 80, 20, 1) / 100
    nb_sim   = cf3.selectbox("Simulations", [500, 1000, 5000], index=1)
    drift_pct= cf4.number_input("Drift (%/an)", -30, 30, 4, 1) / 100

    with st.spinner("Simulation en cours…"):
        res = simulate_autocall(
            product, nb_scenarios=nb_sim,
            vol_override=vol_pct, drift_override=drift_pct, market=market_df,
        )

    # ── KPIs ──
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: _kpi("Prob. rappel", f"{res['prob_rappel_total_pct']:.1f}%", GREEN)
    with c2: _kpi("Prob. knock-in", f"{res['prob_ki_pct']:.1f}%", RED)
    with c3: _kpi("Rendement moyen", f"{res['rendement_estime_pct']:.1f}%", ACCENT)
    with c4: _kpi("Rendement médian", f"{res['rendement_median_pct']:.1f}%", ACCENT)
    with c5: _kpi("Perte max", f"{res['perte_max_pct']:.1f}%", RED)

    st.markdown("<br>", unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["📊 Probabilités de rappel", "📈 Trajectoires", "💰 Distribution payoff"])

    with tab1:
        col_a, col_b = st.columns(2)
        with col_a:
            _sec("PROBABILITÉ DE RAPPEL PAR DATE")
            y = res["prob_rappel_par_date"]
            max_y = max(y) if y else 10
            fig = go.Figure(go.Bar(
                x=res["obs_dates_labels"], y=y,
                marker_color=[ACCENT if v < max_y * 0.8 else GREEN for v in y],
                text=[f"{v:.1f}%" for v in y],
                textposition="outside", textfont=dict(color=TEXT, size=11),
            ))
            _chart(fig, height=300, showlegend=False)
            fig.update_layout(yaxis_title="%", yaxis_range=[0, max_y * 1.35])
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        with col_b:
            _sec("PROB. CUMULÉE + SCÉNARIOS DÉTERMINISTES")
            cum = list(pd.Series(res["prob_rappel_par_date"]).cumsum())
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=res["obs_dates_labels"], y=cum,
                mode="lines+markers", fill="tozeroy",
                fillcolor=_rgba(GREEN, 0.09), line=dict(color=GREEN, width=2),
                marker=dict(color=GREEN, size=8), name="Prob. cumulée",
            ))
            _chart(fig2, height=300, showlegend=True)
            fig2.update_layout(yaxis_title="%", yaxis_range=[0, 100])
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    with tab2:
        _sec(f"TRAJECTOIRES MONTE-CARLO — 50 SUR {nb_sim} + SCÉNARIOS")
        paths = np.array(res["paths_sample"])
        nb_steps = res["nb_steps"]
        x_axis   = list(range(nb_steps))

        fig3 = go.Figure()
        # Trajectoires individuelles
        for i, path in enumerate(paths):
            c = _rgba(GREEN, 0.10) if path[-1] >= 1.0 else _rgba(RED, 0.10)
            fig3.add_trace(go.Scatter(
                x=x_axis, y=(path * 100).tolist(),
                mode="lines", showlegend=False,
                line=dict(color=c, width=1),
            ))
        # Scénarios déterministes
        pal = [GREEN, YELLOW, RED]
        for (label, path_avg), color in zip(res["scenarios_det"].items(), pal):
            fig3.add_trace(go.Scatter(
                x=x_axis, y=(np.array(path_avg) * 100).tolist(),
                mode="lines", name=label,
                line=dict(color=color, width=2.5),
            ))
        # Lignes barrière
        fig3.add_hline(y=res["ki_pct"] * 100, line_color=RED, line_dash="dash", line_width=2,
                       annotation_text=f"KI {res['ki_pct']*100:.0f}%",
                       annotation_font_color=RED, annotation_font_size=11)
        fig3.add_hline(y=res["rappel_pct"] * 100, line_color=GREEN, line_dash="dash", line_width=2,
                       annotation_text=f"Rappel {res['rappel_pct']*100:.0f}%",
                       annotation_font_color=GREEN, annotation_font_size=11)
        fig3.add_hline(y=100, line_color=BORDER, line_width=1)
        fig3.add_hrect(y0=0, y1=res["ki_pct"]*100, fillcolor=_rgba(RED, 0.06), line_width=0)

        _chart(fig3, height=420)
        fig3.update_layout(yaxis_title="Cours (% du strike)", xaxis_title="Jours ouvrés")
        st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})

    with tab3:
        _sec("DISTRIBUTION DES RENDEMENTS FINAUX (500 SCÉNARIOS)")
        payoffs = res["payoffs_sample"]
        fig4 = go.Figure()
        fig4.add_trace(go.Histogram(
            x=payoffs, nbinsx=40,
            marker_color=ACCENT, marker_line_color=BG, marker_line_width=1,
            name="Rendement (%)",
        ))
        fig4.add_vline(x=0, line_color=BORDER, line_width=2)
        fig4.add_vline(x=res["rendement_estime_pct"], line_color=GREEN, line_dash="dash",
                       annotation_text=f"Moyenne {res['rendement_estime_pct']:.1f}%",
                       annotation_font_color=GREEN)
        perte_min = min(payoffs)
        if perte_min < -5:
            fig4.add_vrect(x0=perte_min, x1=0, fillcolor=_rgba(RED, 0.10), line_width=0)
        _chart(fig4, height=340)
        fig4.update_layout(
            xaxis_title="Rendement total (%)", yaxis_title="Nb scénarios", showlegend=False,
        )
        st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar": False})

        # Stats clés
        arr = np.array(payoffs)
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Rendement moyen",   f"{arr.mean():.1f}%")
        s2.metric("Médiane",           f"{np.median(arr):.1f}%")
        s3.metric("Scén. positifs",    f"{(arr>0).mean()*100:.0f}%")
        s4.metric("VaR 95% (perte)",   f"{np.percentile(arr, 5):.1f}%")


# ── PAGE : Vue Clients ────────────────────────────────────────────────────────
def _client_import_panel(engine) -> None:
    with st.expander("Importer clients / positions CSV", expanded=False):
        st.caption(
            "Colonnes attendues : nom, date_souscription, nominal_souscrit, "
            "et produit_id ou isin ou produit. Optionnel : prenom, profil, segment, prix_souscription."
        )
        c_tpl, c_upload = st.columns([1, 2])
        with c_tpl:
            st.download_button(
                "Télécharger modèle CSV",
                data=sample_client_positions_csv(),
                file_name="modele_import_clients_positions.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with c_upload:
            uploaded = st.file_uploader(
                "Fichier CSV",
                type=["csv"],
                key="client_positions_csv",
                label_visibility="collapsed",
            )

        if uploaded is not None:
            try:
                preview = pd.read_csv(uploaded, sep=None, engine="python")
            except Exception as exc:
                st.error(f"CSV illisible : {exc}")
                return
            st.dataframe(preview.head(20), use_container_width=True, hide_index=True)
            if st.button("Importer dans la base", type="primary", use_container_width=True):
                result = import_client_positions(engine, preview)
                if result.errors:
                    st.error(f"{len(result.errors)} erreur(s) détectée(s).")
                    st.write(result.errors[:10])
                if result.positions_upserted:
                    st.success(
                        f"{result.positions_upserted} position(s) importée(s) / mise(s) à jour, "
                        f"{result.clients_created} client(s) créé(s)."
                    )
                    st.rerun()


def page_clients(engine, market_df: pd.DataFrame):
    _header("Vue Clients", "Exposition par client, alertes risque et analyse de portefeuille")
    _client_import_panel(engine)

    positions = load_positions(engine)
    enriched  = enrich_products_with_market(load_products(engine), market_df)
    if positions.empty:
        st.warning("Aucune position.")
        return

    positions = positions.merge(
        enriched[[
            "produit_id", "statut", "dist_barriere_ki_pct", "worst_of_pct",
            "score_risque", "point_attention"
        ]],
        on="produit_id", how="left",
    )

    # ── Alertes ──
    alertes = positions[positions["statut"].isin(["DANGER", "KI_DECLENCHE"])]
    if not alertes.empty:
        clients_alerte = alertes.groupby("client")["nominal_souscrit"].sum()
        alert_html = "".join([
            f'<span style="background:{RED}22;color:{RED};border:1px solid {RED};border-radius:4px;padding:3px 10px;font-size:12px;font-weight:600;margin:3px;">'
            f'⚠ {c} — {v/1000:.0f}k€ à risque</span>'
            for c, v in clients_alerte.items()
        ])
        st.markdown(f"""
        <div style="background:#1a0a0a;border:1px solid {RED};border-radius:8px;
                    padding:12px 16px;margin-bottom:16px;">
          <div style="color:{RED};font-weight:700;font-size:12px;margin-bottom:6px;">
            ALERTES — {len(clients_alerte)} client(s) avec produits en danger
          </div>
          <div style="display:flex;flex-wrap:wrap;gap:4px;">{alert_html}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── KPIs ──
    enc_total = positions["nominal_souscrit"].sum()
    nb_clients= positions["client_id"].nunique()
    enc_risque= positions[positions["statut"].isin(["DANGER","KI_DECLENCHE"])]["nominal_souscrit"].sum()
    coupon_moy= positions["coupon_annuel_pct"].mean()

    c1, c2, c3, c4 = st.columns(4)
    with c1: _kpi("Encours total", f"{enc_total/1e6:.1f}M €", ACCENT)
    with c2: _kpi("Clients actifs", str(nb_clients))
    with c3: _kpi("Encours à risque", f"{enc_risque/1e3:.0f}k €", RED if enc_risque > 0 else TEXT,
                   sub=f"{enc_risque/enc_total*100:.1f}% du total" if enc_total > 0 else "")
    with c4: _kpi("Coupon moy. port.", f"{coupon_moy:.1f}%/an", ACCENT)

    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)

    with col_a:
        _sec("ENCOURS PAR CLIENT — COULEUR = RISQUE MAX")
        enc_c = positions.groupby("client").agg(
            nominal=("nominal_souscrit", "sum"),
            score_max=("score_risque", "max"),
        ).reset_index().sort_values("nominal", ascending=True)
        bar_c = [GREEN if s < 30 else (YELLOW if s < 60 else RED) for s in enc_c["score_max"]]
        fig = go.Figure(go.Bar(
            x=enc_c["nominal"] / 1000, y=enc_c["client"],
            orientation="h", marker_color=bar_c,
            text=(enc_c["nominal"] / 1000).apply(lambda x: f"{x:.0f}k€"),
            textposition="outside", textfont=dict(color=TEXT, size=11),
        ))
        _chart(fig, height=320)
        fig.update_layout(showlegend=False, xaxis_title="Nominal (k€)")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col_b:
        _sec("ALLOCATION PAR TYPE DE PRODUIT")
        enc_t = positions.groupby("type_produit")["nominal_souscrit"].sum().reset_index()
        type_labels = [TYPE_LABEL.get(t, t) for t in enc_t["type_produit"]]
        fig2 = go.Figure(go.Pie(
            labels=type_labels, values=enc_t["nominal_souscrit"],
            hole=0.6, marker=dict(colors=CHART_C, line=dict(color=BG, width=2)),
            textfont=dict(color=TEXT, size=12),
        ))
        fig2.update_layout(
            height=320, paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=MUTED, size=11)),
        )
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    # ── Détail client ──
    _sec("PORTEFEUILLE DÉTAILLÉ PAR CLIENT")
    clients = sorted(positions["client"].unique())
    client_sel = st.selectbox("Sélectionner un client", clients)
    cp = positions[positions["client"] == client_sel]
    if cp.empty:
        return

    profil   = cp["profil"].iloc[0]
    segment  = cp["segment"].iloc[0]
    enc_c_v  = cp["nominal_souscrit"].sum()
    score_c  = int(cp["score_risque"].max())
    score_cc = GREEN if score_c < 30 else (YELLOW if score_c < 60 else RED)

    st.markdown(f"""
    <div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:10px;
                padding:16px 20px;margin-bottom:14px;">
      <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:16px;font-size:12px;">
        <div><div style="color:{MUTED};font-size:10px;">PROFIL</div>
             <div style="color:{TEXT};font-weight:600;">{profil.capitalize()}</div></div>
        <div><div style="color:{MUTED};font-size:10px;">SEGMENT</div>
             <div style="color:{TEXT};font-weight:600;">{segment.capitalize()}</div></div>
        <div><div style="color:{MUTED};font-size:10px;">ENCOURS</div>
             <div style="color:{ACCENT};font-weight:700;">{enc_c_v/1000:.0f}k €</div></div>
        <div><div style="color:{MUTED};font-size:10px;">PRODUITS</div>
             <div style="color:{TEXT};font-weight:600;">{len(cp)}</div></div>
        <div><div style="color:{MUTED};font-size:10px;">SCORE RISQUE MAX</div>
             <div style="color:{score_cc};font-weight:700;">{score_c}/100</div>
             <div style="width:100%;background:#1c2230;border-radius:4px;height:5px;overflow:hidden;">
               <div style="width:{score_c}%;background:{score_cc};height:100%;border-radius:4px;"></div>
             </div></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    pitch_export = cp.copy()
    pitch_export["adequation"] = pitch_export.apply(
        lambda r: suitability_score(
            r.get("profil"), r.get("type_produit"), int(_f(r.get("score_risque"))),
            int(_f(r.get("jours_restants"))) if "jours_restants" in r else None,
        )[1],
        axis=1,
    )
    export_cols = [
        "client", "profil", "segment", "produit", "type_produit",
        "nominal_souscrit", "coupon_annuel_pct", "date_echeance",
        "statut", "score_risque", "adequation", "main_risk", "next_action",
    ]
    _download_csv(
        "Exporter la fiche client",
        pitch_export[[c for c in export_cols if c in pitch_export.columns]],
        f"fiche_client_{client_sel.replace(' ', '_')}.csv",
    )

    for _, row in cp.sort_values("score_risque", ascending=False).iterrows():
        s_color = STATUT_COLOR.get(row.get("statut", "N/A"), MUTED)
        dist    = _f(row.get("dist_barriere_ki_pct"))
        sc      = int(_f(row.get("score_risque")))
        sc_c    = GREEN if sc < 30 else (YELLOW if sc < 60 else RED)
        adequation_score, adequation_label = suitability_score(
            row.get("profil"), row.get("type_produit"), sc, None
        )
        adequation_color = GREEN if adequation_label == "Adapté" else (YELLOW if adequation_label == "À discuter" else RED)

        st.markdown(f"""
        <div style="background:{BG_CARD2};border:1px solid {BORDER};
                    border-left:3px solid {s_color};
                    border-radius:8px;padding:14px 18px;margin-bottom:8px;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
              <div style="color:{TEXT};font-weight:700;font-size:13px;">{row['produit']}</div>
              <div style="color:{MUTED};font-size:11px;margin-top:2px;">
                {TYPE_LABEL.get(row['type_produit'],row['type_produit'])} · {row['sous_jacent_1']}
                · Souscrit {_v(row.get('date_souscription'),'?')}
              </div>
            </div>
            {_badge(row.get('statut','N/A'))}
          </div>
          <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px;
                      font-size:12px;margin-top:12px;">
            <div>
              <div style="color:{MUTED};font-size:10px;">NOMINAL</div>
              <div style="color:{TEXT};font-weight:600;">{row['nominal_souscrit']/1000:.0f}k €</div>
            </div>
            <div>
              <div style="color:{MUTED};font-size:10px;">COUPON /AN</div>
              <div style="color:{ACCENT};font-weight:600;">{row['coupon_annuel_pct']:.1f}%</div>
            </div>
            <div>
              <div style="color:{MUTED};font-size:10px;">DIST. BARRIÈRE KI</div>
              <div style="color:{s_color};font-weight:700;">{dist:.1f}%</div>
            </div>
            <div>
              <div style="color:{MUTED};font-size:10px;">ÉCHÉANCE</div>
              <div style="color:{TEXT};font-size:11px;">{_v(row.get('date_echeance'),'—')}</div>
            </div>
            <div>
              <div style="color:{MUTED};font-size:10px;">SCORE RISQUE</div>
              <div style="color:{sc_c};font-weight:700;">{sc}/100</div>
              <div style="width:100%;background:#1c2230;border-radius:4px;height:5px;overflow:hidden;">
                <div style="width:{sc}%;background:{sc_c};height:100%;border-radius:4px;"></div>
              </div>
            </div>
          </div>
          <div style="margin-top:10px;background:{BG_CARD};border:1px solid {BORDER};border-radius:6px;padding:8px 10px;font-size:11px;">
            <span style="color:{adequation_color};font-weight:700;">Adéquation : {adequation_label} ({adequation_score}/100)</span>
            <span style="color:{MUTED};"> · {_v(row.get('next_action'), _v(row.get('point_attention'), 'Action à qualifier'))}</span>
          </div>
        </div>
        """, unsafe_allow_html=True)


def page_pitch_client(engine, market_df: pd.DataFrame):
    _maybe_demo("Pitch Client")
    _header("Pitch Client", "Préparer une recommandation commerciale adaptée au profil client")

    positions = load_positions(engine)
    products = load_products(engine)
    enriched = enrich_products_with_market(products, market_df)
    if positions.empty or enriched.empty:
        st.warning("Données client ou produits indisponibles.")
        return

    clients = sorted(positions["client"].unique())
    client_sel = st.selectbox("Client", clients)
    cp = positions[positions["client"] == client_sel].copy()
    profil = cp["profil"].iloc[0]
    segment = cp["segment"].iloc[0]
    encours = cp["nominal_souscrit"].sum()

    scored = enriched.copy()
    scored[["adequation_score", "adequation"]] = scored.apply(
        lambda r: pd.Series(
            suitability_score(
                profil,
                r.get("type_produit"),
                int(_f(r.get("score_risque"))),
                int(_f(r.get("jours_restants"))),
            )
        ),
        axis=1,
    )
    already = set(cp["produit_id"].tolist())
    candidates = scored[~scored["produit_id"].isin(already)].sort_values(
        ["adequation_score", "coupon_annuel_pct"], ascending=[False, False]
    )

    risky = cp.merge(
        enriched[["produit_id", "statut", "score_risque", "point_attention"]],
        on="produit_id", how="left"
    )
    risky = risky[(risky["score_risque"] >= 60) | (risky["statut"].isin(["DANGER", "KI_DECLENCHE"]))]
    cln_expo = cp[cp["type_produit"] == "cln"]["nominal_souscrit"].sum()
    cln_pct = cln_expo / encours * 100 if encours else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1: _kpi("Client", client_sel)
    with c2: _kpi("Profil", str(profil).capitalize(), ACCENT)
    with c3: _kpi("Encours", f"{encours/1000:.0f}k €", TEXT)
    with c4: _kpi("Exposition CLN", f"{cln_pct:.0f}%", YELLOW if cln_pct > 30 else GREEN)

    _sec("SYNTHÈSE SALES")
    alerts = []
    if not risky.empty:
        alerts.append(f"{len(risky)} produit(s) à surveiller en priorité.")
    if cln_pct > 35:
        alerts.append("Exposition CLN élevée : éviter d'ajouter du risque crédit.")
    if not alerts:
        alerts.append("Portefeuille équilibré : possibilité d'étudier une nouvelle idée selon le profil.")

    st.markdown(f"""
    <div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:10px;padding:14px 18px;margin-bottom:12px;">
      <div style="color:{TEXT};font-size:13px;line-height:1.55;">{"<br>".join(alerts)}</div>
    </div>
    """, unsafe_allow_html=True)

    col_a, col_b = st.columns([3, 2])
    with col_a:
        _sec("3 IDÉES PRODUITS À PRÉSENTER")
        for _, row in candidates.head(3).iterrows():
            color = GREEN if row["adequation"] == "Adapté" else YELLOW
            _, payoff, action = _family_pitch(row)
            pitch = generate_sales_pitch(
                {"client": client_sel, "profil": profil, "segment": segment},
                row,
            )
            st.markdown(f"""
            <div style="background:{BG_CARD};border:1px solid {BORDER};border-left:3px solid {color};border-radius:9px;padding:13px 16px;margin-bottom:9px;">
              <div style="display:flex;justify-content:space-between;gap:12px;">
                <div>
                  <div style="color:{TEXT};font-weight:700;font-size:13px;">{row['nom']}</div>
                  <div style="color:{MUTED};font-size:11px;margin-top:2px;">{TYPE_LABEL.get(row['type_produit'], row['type_produit'])} · Coupon {row['coupon_annuel_pct']:.1f}% · Score risque {int(row['score_risque'])}/100</div>
                </div>
                <div style="color:{color};font-size:12px;font-weight:700;">{row['adequation']}<br>{int(row['adequation_score'])}/100</div>
              </div>
              <div style="color:{TEXT};font-size:11px;line-height:1.45;margin-top:8px;">{payoff}</div>
              <div style="color:{ACCENT};font-size:11px;line-height:1.45;margin-top:5px;">Action : {action}</div>
            </div>
            """, unsafe_allow_html=True)
            pitch_block(pitch)

    with col_b:
        _sec("À ÉVITER / SURVEILLER")
        if risky.empty:
            st.success("Aucune alerte majeure sur le portefeuille actuel.")
        else:
            for _, row in risky.sort_values("score_risque", ascending=False).iterrows():
                st.markdown(f"""
                <div style="background:{BG_CARD};border:1px solid {RED};border-radius:8px;padding:10px 12px;margin-bottom:8px;">
                  <div style="color:{TEXT};font-size:12px;font-weight:700;">{row['produit']}</div>
                  <div style="color:{RED};font-size:11px;margin-top:3px;">Score {int(_f(row.get('score_risque')))} · {_v(row.get('point_attention'), 'Surveillance requise')}</div>
                </div>
                """, unsafe_allow_html=True)

    export = candidates.head(5)[[
        "nom", "type_produit", "coupon_annuel_pct", "date_echeance",
        "score_risque", "adequation_score", "adequation",
        "payoff_summary", "sales_argument", "main_risk", "next_action",
    ]].copy()
    _download_csv("Exporter le pitch client", export, f"pitch_{client_sel.replace(' ', '_')}.csv")


def page_meeting_pack(engine, market_df: pd.DataFrame):
    _maybe_demo("Meeting Pack")
    _header("Meeting Pack", "Préparer un rendez-vous client avec visuels, alertes, idée produit et pitch")

    positions = load_positions(engine)
    products = load_products(engine)
    enriched = enrich_products_with_market(products, market_df)
    alerts = build_sales_alerts(positions, enriched, market_df)
    if positions.empty or enriched.empty:
        st.warning("Données client ou produits indisponibles.")
        return

    clients = sorted(positions["client"].unique())
    client_sel = st.selectbox("Client à préparer", clients)
    cp = positions[positions["client"] == client_sel].copy()
    profil = cp["profil"].iloc[0]
    segment = cp["segment"].iloc[0]
    encours = float(cp["nominal_souscrit"].sum())

    scored = enriched.copy()
    scored[["adequation_score", "adequation"]] = scored.apply(
        lambda r: pd.Series(
            suitability_score(
                profil,
                r.get("type_produit"),
                int(_f(r.get("score_risque"))),
                int(_f(r.get("jours_restants"))),
            )
        ),
        axis=1,
    )
    already = set(cp["produit_id"].tolist())
    candidates = scored[~scored["produit_id"].isin(already)].sort_values(
        ["adequation_score", "coupon_annuel_pct"],
        ascending=[False, False],
    )
    selected_product = candidates.iloc[0] if not candidates.empty else scored.sort_values("score_risque").iloc[0]
    pitch = generate_sales_pitch(
        {"client": client_sel, "profil": profil, "segment": segment},
        selected_product,
    )

    cp_enriched = cp.merge(
        enriched[["produit_id", "score_risque", "statut", "point_attention", "dist_barriere_ki_pct"]],
        on="produit_id",
        how="left",
    )
    max_risk = int(_f(cp_enriched["score_risque"].max()))
    client_alerts = alerts[alerts["client"] == client_sel].copy()
    cln_expo = float(cp[cp["type_produit"] == "cln"]["nominal_souscrit"].sum())
    cln_pct = cln_expo / encours * 100 if encours else 0

    st.markdown(f"""
<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:14px;padding:18px 22px;margin-bottom:16px;">
  <div style="display:flex;justify-content:space-between;gap:20px;align-items:flex-start;">
    <div>
      <div style="color:{MUTED};font-size:10px;text-transform:uppercase;letter-spacing:.10em;">Pack rendez-vous</div>
      <div style="color:{TEXT};font-size:24px;font-weight:800;margin-top:3px;">{client_sel}</div>
      <div style="color:{MUTED};font-size:12px;margin-top:4px;">Profil {str(profil).capitalize()} · Segment {str(segment).capitalize()} · {len(cp)} produit(s) en portefeuille</div>
    </div>
    <div style="min-width:190px;">
      <div style="color:{_risk_color(max_risk)};font-weight:800;text-align:right;">Risque max {max_risk}/100</div>
      <div style="width:100%;background:#1c2230;border-radius:5px;height:7px;overflow:hidden;margin-top:6px;">
        <div style="width:{max_risk}%;background:{_risk_color(max_risk)};height:100%;border-radius:5px;"></div>
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1: _kpi("Encours client", f"{encours/1000:.0f}k €", ACCENT)
    with c2: _kpi("Alertes", str(len(client_alerts)), RED if len(client_alerts) else GREEN)
    with c3: _kpi("Exposition CLN", f"{cln_pct:.0f}%", YELLOW if cln_pct > 30 else GREEN)
    with c4: _kpi("Idée top", f"{int(_f(selected_product.get('adequation_score')))} /100", GREEN)

    st.markdown("<br>", unsafe_allow_html=True)
    col_left, col_right = st.columns([1.25, 1])
    with col_left:
        _sec("PORTEFEUILLE CLIENT — ENCOURS ET RISQUE")
        port = cp_enriched.groupby(["produit", "type_produit"]).agg(
            nominal=("nominal_souscrit", "sum"),
            score=("score_risque", "max"),
        ).reset_index().sort_values("nominal", ascending=True)
        fig = go.Figure(go.Bar(
            x=port["nominal"] / 1000,
            y=port["produit"].str[:36],
            orientation="h",
            marker_color=[_risk_color(int(_f(s))) for s in port["score"]],
            text=(port["nominal"] / 1000).apply(lambda x: f"{x:.0f}k€"),
            textposition="outside",
            textfont=dict(color=TEXT, size=11),
        ))
        _chart(fig, height=max(280, len(port) * 58))
        fig.update_layout(showlegend=False, xaxis_title="Nominal (k€)", yaxis_title="")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col_right:
        _sec("ALERTES À TRAITER")
        if client_alerts.empty:
            st.success("Aucune alerte majeure pour ce client.")
        else:
            for _, row in client_alerts.head(4).iterrows():
                color = RED if row["priorite"] == "Haute" else YELLOW
                st.markdown(f"""
<div style="background:{BG_CARD};border:1px solid {BORDER};border-left:3px solid {color};border-radius:9px;padding:11px 13px;margin-bottom:8px;">
  <div style="color:{color};font-size:11px;font-weight:800;">{row['priorite']}</div>
  <div style="color:{TEXT};font-size:12px;font-weight:700;margin-top:2px;">{row['produit']}</div>
  <div style="color:{MUTED};font-size:11px;margin-top:4px;line-height:1.4;">{row['raison']}</div>
</div>
""", unsafe_allow_html=True)

    col_idea, col_payoff = st.columns([1, 1])
    with col_idea:
        _sec("IDÉE PRODUIT À PRÉSENTER")
        score = int(_f(selected_product.get("score_risque")))
        adequation = _v(selected_product.get("adequation"), "À qualifier")
        st.markdown(f"""
<div style="background:{BG_CARD};border:1px solid {BORDER};border-left:3px solid {GREEN};border-radius:10px;padding:15px 17px;margin-bottom:12px;">
  <div style="display:flex;justify-content:space-between;gap:12px;">
    <div>
      <div style="color:{TEXT};font-weight:800;font-size:15px;">{selected_product['nom']}</div>
      <div style="color:{MUTED};font-size:11px;margin-top:3px;">{TYPE_LABEL.get(selected_product['type_produit'], selected_product['type_produit'])} · {selected_product['sous_jacent_1']}</div>
    </div>
    <div style="color:{GREEN};font-weight:800;text-align:right;">{adequation}<br>{int(_f(selected_product.get('adequation_score')))} /100</div>
  </div>
  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:13px;font-size:12px;">
    <div><div style="color:{MUTED};font-size:10px;">COUPON</div><div style="color:{ACCENT};font-weight:800;">{_f(selected_product.get('coupon_annuel_pct')):.1f}%</div></div>
    <div><div style="color:{MUTED};font-size:10px;">RISQUE</div><div style="color:{_risk_color(score)};font-weight:800;">{score}/100</div></div>
    <div><div style="color:{MUTED};font-size:10px;">MATURITÉ</div><div style="color:{TEXT};font-weight:700;">{int(_f(selected_product.get('jours_restants')))}j</div></div>
  </div>
  <div style="color:{TEXT};font-size:12px;line-height:1.45;margin-top:12px;">{_v(selected_product.get('payoff_summary'))}</div>
</div>
""", unsafe_allow_html=True)
        st.info(pitch)

    with col_payoff:
        _sec("PAYOFF VISUEL")
        st.plotly_chart(_payoff_profile_fig(selected_product), use_container_width=True, config={"displayModeBar": False})

    col_stress, col_export = st.columns([1.25, 1])
    with col_stress:
        _sec("STRESS TEST SYNTHÉTIQUE")
        stress = stress_test_product(selected_product)
        colors = [RED if v < 0 else GREEN for v in stress["perte_indicative_pct"]]
        fig2 = go.Figure(go.Bar(
            x=stress["scenario"],
            y=stress["perte_indicative_pct"],
            marker_color=colors,
            text=stress["statut"],
            textposition="outside",
            textfont=dict(color=TEXT, size=10),
        ))
        _chart(fig2, height=280)
        fig2.update_layout(showlegend=False, xaxis_title="Scénario sous-jacent", yaxis_title="Perte indicative (%)")
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    with col_export:
        _sec("EXPORT RENDEZ-VOUS")
        pack_rows = pd.DataFrame([
            {"Bloc": "Client", "Synthèse": f"{client_sel} · profil {profil} · encours {encours/1000:.0f}k EUR"},
            {"Bloc": "Alertes", "Synthèse": f"{len(client_alerts)} alerte(s) à traiter"},
            {"Bloc": "Idée", "Synthèse": f"{selected_product['nom']} · coupon {_f(selected_product.get('coupon_annuel_pct')):.1f}% · risque {score}/100"},
            {"Bloc": "Pitch", "Synthèse": pitch},
        ])
        st.dataframe(pack_rows, use_container_width=True, hide_index=True)
        c_csv, c_html = st.columns(2)
        with c_csv:
            _download_csv("Export CSV", pack_rows, f"meeting_pack_{client_sel.replace(' ', '_')}.csv")
        with c_html:
            html_doc = build_meeting_pack_html(
                client_sel, str(profil), str(segment), encours, max_risk,
                client_alerts, selected_product, pitch,
            )
            st.download_button(
                "Export HTML (imprimable)",
                data=html_doc.encode("utf-8"),
                file_name=f"meeting_pack_{client_sel.replace(' ', '_')}.html",
                mime="text/html",
                use_container_width=True,
            )
        if st.session_state.get("demo_mode") and int(st.session_state.get("demo_step", 0)) >= len(_DEMO_STEPS) - 1:
            if st.button("Terminer la démo entretien", use_container_width=True):
                st.session_state["demo_mode"] = False
                st.session_state["demo_step"] = 0
                st.success("Démo terminée — bon entretien !")


# ── PAGE : Screener ───────────────────────────────────────────────────────────
def page_screener(market_df: pd.DataFrame, engine):
    _header("Screener Sous-jacents",
            "Sélectionner le bon sous-jacent selon vol, RSI, tendance — et obtenir une recommandation produit")

    last = market_df.sort_values("date_cours").groupby("ticker").last().reset_index()
    last["vol_ann"] = last["volatilite_20j"] * (252**0.5) * 100

    # ── Filtres ──
    st.markdown(f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:10px;padding:16px 20px;margin-bottom:16px;">', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)
    vol_min = c1.slider("Vol. min (%)",  0,  40, 0)
    vol_max = c2.slider("Vol. max (%)",  5,  60, 40)
    rsi_min = c3.slider("RSI min",       0, 100, 0)
    rsi_max = c4.slider("RSI max",       0, 100, 100)
    types_f = c5.multiselect("Type", last["type_instrument"].unique().tolist(),
                               default=last["type_instrument"].unique().tolist())
    st.markdown("</div>", unsafe_allow_html=True)

    f = last.dropna(subset=["vol_ann","rsi_14"])
    f = f[(f["vol_ann"]>=vol_min)&(f["vol_ann"]<=vol_max)&(f["rsi_14"]>=rsi_min)&(f["rsi_14"]<=rsi_max)&(f["type_instrument"].isin(types_f))]

    st.markdown(f'<div style="color:{MUTED};font-size:12px;margin-bottom:12px;">{len(f)} instrument(s) sélectionné(s)</div>', unsafe_allow_html=True)

    col_a, col_b = st.columns([3, 2])

    with col_a:
        _sec("MATRICE RSI × VOLATILITÉ")
        type_c = {"action": ACCENT, "indice": GREEN, "etf": YELLOW, "devise": PURPLE}
        fig = go.Figure()
        for itype, grp in f.groupby("type_instrument"):
            fig.add_trace(go.Scatter(
                x=grp["vol_ann"], y=grp["rsi_14"],
                mode="markers+text", text=grp["ticker"],
                textposition="top center", textfont=dict(size=10, color=MUTED),
                marker=dict(size=13, color=type_c.get(itype, ACCENT),
                            line=dict(color=BG, width=1.5)),
                name=itype.capitalize(),
            ))
        # Zones colorées
        fig.add_hrect(y0=70, y1=100, fillcolor=_rgba(RED, 0.07),   line_width=0)
        fig.add_hrect(y0=0,  y1=30,  fillcolor=_rgba(GREEN, 0.07), line_width=0)
        fig.add_hline(y=70, line_color=RED,   line_dash="dash", line_width=1,
                      annotation_text="Surachat", annotation_font_color=RED)
        fig.add_hline(y=30, line_color=GREEN, line_dash="dash", line_width=1,
                      annotation_text="Survente", annotation_font_color=GREEN)
        _chart(fig, height=420)
        fig.update_layout(xaxis_title="Volatilité ann. (%)", yaxis_title="RSI (14j)", yaxis_range=[0,100])
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col_b:
        _sec("RECOMMANDATION PRODUIT STRUCTURÉ")
        for _, row in f.sort_values("vol_ann").iterrows():
            vol_v = row["vol_ann"]
            rsi_v = row["rsi_14"]
            sig   = _v(row.get("signal_tendance"), "—")

            # Recommandation selon profil
            if vol_v > 25 and rsi_v < 50:
                reco = "Autocall ou CLN — vol/spread élevés = coupon attractif"
                reco_c = ACCENT
            elif vol_v < 15:
                reco = "Capital Protégé — vol faible = protection abordable"
                reco_c = GREEN
            elif rsi_v > 65:
                reco = "Reverse Convertible — sous-jacent haussier"
                reco_c = YELLOW
            else:
                reco = "Autocall step-down — profil neutre"
                reco_c = MUTED

            vol_c = RED if vol_v > 30 else (YELLOW if vol_v > 20 else GREEN)
            rsi_c = RED if rsi_v > 70 else (GREEN if rsi_v < 30 else MUTED)

            st.markdown(f"""
            <div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;
                        padding:12px 14px;margin-bottom:8px;">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <div>
                  <span style="color:{TEXT};font-weight:700;font-size:13px;">{row['ticker']}</span>
                  <span style="color:{MUTED};font-size:11px;margin-left:6px;">{_v(row.get('nom'),'')[:25]}</span>
                </div>
                <span style="color:{GREEN if sig=='Au-dessus SMA50' else RED};font-size:11px;font-weight:600;">
                  {sig}
                </span>
              </div>
              <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;font-size:11px;margin-bottom:8px;">
                <div style="text-align:center;background:{BG_CARD2};border-radius:6px;padding:6px;">
                  <div style="color:{MUTED};font-size:9px;">VOLATILITÉ</div>
                  <div style="color:{vol_c};font-weight:700;">{vol_v:.1f}%</div>
                </div>
                <div style="text-align:center;background:{BG_CARD2};border-radius:6px;padding:6px;">
                  <div style="color:{MUTED};font-size:9px;">RSI</div>
                  <div style="color:{rsi_c};font-weight:700;">{rsi_v:.0f}</div>
                </div>
                <div style="text-align:center;background:{BG_CARD2};border-radius:6px;padding:6px;">
                  <div style="color:{MUTED};font-size:9px;">SMA50</div>
                  <div style="color:{TEXT};font-weight:600;font-size:10px;">
                    {"↑" if sig=="Au-dessus SMA50" else "↓"}
                  </div>
                </div>
              </div>
              <div style="background:{reco_c}18;border:1px solid {reco_c}44;border-radius:6px;
                          padding:6px 10px;font-size:11px;color:{reco_c};">
                💡 {reco}
              </div>
            </div>
            """, unsafe_allow_html=True)


def _product_card(row, extra_html: str = ""):
    score = int(_f(row.get("score_risque")))
    score_c = GREEN if score < 30 else (YELLOW if score < 60 else RED)
    label = TYPE_LABEL.get(row.get("type_produit"), row.get("type_produit"))
    extra_html = extra_html.strip()
    card_html = f"""
<div style="background:{BG_CARD};border:1px solid {BORDER};border-left:3px solid {score_c};
            border-radius:10px;padding:14px 16px;margin-bottom:10px;">
  <div style="display:flex;justify-content:space-between;gap:16px;">
    <div>
      <div style="color:{TEXT};font-size:14px;font-weight:800;">{row['nom']}</div>
      <div style="color:{MUTED};font-size:11px;margin-top:2px;">{label} · {row['sous_jacent_1']} · Coupon {row['coupon_annuel_pct']:.1f}%</div>
    </div>
    <div style="min-width:120px;text-align:right;">
      <div style="color:{score_c};font-weight:800;font-size:13px;">Risque {score}/100</div>
      <div style="width:100%;background:#1c2230;border-radius:4px;height:5px;overflow:hidden;">
        <div style="width:{score}%;background:{score_c};height:100%;border-radius:4px;"></div>
      </div>
    </div>
  </div>
  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:12px;font-size:11px;">
    <div style="background:{BG_CARD2};border:1px solid {BORDER};border-radius:6px;padding:8px;">
      <div style="color:{ACCENT};font-weight:700;margin-bottom:4px;">Payoff</div>
      <div style="color:{TEXT};line-height:1.35;">{_v(row.get('payoff_summary'), 'Payoff à qualifier')}</div>
    </div>
    <div style="background:{BG_CARD2};border:1px solid {BORDER};border-radius:6px;padding:8px;">
      <div style="color:{YELLOW};font-weight:700;margin-bottom:4px;">Risque</div>
      <div style="color:{TEXT};line-height:1.35;">{_v(row.get('main_risk'), _v(row.get('point_attention'), 'Risque à qualifier'))}</div>
    </div>
    <div style="background:{BG_CARD2};border:1px solid {BORDER};border-radius:6px;padding:8px;">
      <div style="color:{GREEN};font-weight:700;margin-bottom:4px;">Action</div>
      <div style="color:{TEXT};line-height:1.35;">{_v(row.get('next_action'), 'Action à définir')}</div>
    </div>
  </div>
</div>
"""
    st.markdown(card_html, unsafe_allow_html=True)
    if extra_html:
        st.info(extra_html)


def page_book_produits(engine, market_df: pd.DataFrame):
    _maybe_demo("Book Produits")
    _header("Book Produits", "Bibliothèque commerciale avec recherche, filtres, pitch et stress tests")
    enriched = enrich_products_with_market(load_products(engine), market_df)
    if enriched.empty:
        st.warning("Aucun produit disponible.")
        return

    c1, c2, c3 = st.columns([2, 2, 1])
    query = c1.text_input("Recherche", placeholder="Nom, ISIN, sous-jacent...")
    types = sorted(enriched["type_produit"].unique().tolist())
    type_filter = c2.multiselect("Type produit", types, default=types)
    max_risk = c3.slider("Risque max", 0, 100, 100)

    filtered = enriched[enriched["type_produit"].isin(type_filter) & (enriched["score_risque"] <= max_risk)].copy()
    if query:
        q = query.lower()
        filtered = filtered[
            filtered["nom"].str.lower().str.contains(q, na=False)
            | filtered["isin"].astype(str).str.lower().str.contains(q, na=False)
            | filtered["sous_jacent_1"].astype(str).str.lower().str.contains(q, na=False)
        ]

    _download_csv("Exporter le book filtré", filtered, "book_produits.csv")
    for _, row in filtered.sort_values(["type_produit", "score_risque"]).iterrows():
        stress = stress_test_product(row)
        pitch = generate_sales_pitch({"client": "un client cible", "profil": "equilibre"}, row)
        extra = f"Pitch 30 sec : {pitch}"
        _product_card(row, extra)
        with st.expander(f"Stress tests — {row['nom']}"):
            st.dataframe(stress, use_container_width=True, hide_index=True)
            if str(row.get("type_produit", "")) not in ("capital_protected", "cln"):
                bfig = _barrier_monitor_fig(row, market_df)
                if bfig:
                    st.plotly_chart(bfig, use_container_width=True, config={"displayModeBar": False})


def page_alertes_sales(engine, market_df: pd.DataFrame):
    _header("Alertes Sales", "Clients à appeler aujourd’hui et actions recommandées")
    positions = load_positions(engine)
    enriched = enrich_products_with_market(load_products(engine), market_df)
    alerts = build_sales_alerts(positions, enriched, market_df)
    c1, c2, c3 = st.columns(3)
    with c1: _kpi("Alertes", str(len(alerts)), RED if len(alerts) else GREEN)
    with c2: _kpi("Priorité haute", str((alerts["priorite"] == "Haute").sum()) if not alerts.empty else "0", RED)
    with c3: _kpi("Clients concernés", str(alerts["client"].nunique()) if not alerts.empty else "0", ACCENT)

    if alerts.empty:
        st.success("Aucune alerte sales majeure aujourd’hui.")
        return
    _download_csv("Exporter les alertes", alerts, "alertes_sales.csv")
    for _, row in alerts.sort_values("priorite").iterrows():
        color = RED if row["priorite"] == "Haute" else YELLOW
        st.markdown(f"""
        <div style="background:{BG_CARD};border:1px solid {BORDER};border-left:3px solid {color};
                    border-radius:9px;padding:12px 14px;margin-bottom:8px;">
          <div style="display:flex;justify-content:space-between;">
            <div style="color:{TEXT};font-weight:800;">{row['client']} · {row['produit']}</div>
            <div style="color:{color};font-weight:800;">{row['priorite']}</div>
          </div>
          <div style="color:{MUTED};font-size:12px;margin-top:5px;">{row['raison']}</div>
          <div style="color:{ACCENT};font-size:12px;margin-top:5px;">Action : {row['action']}</div>
        </div>
        """, unsafe_allow_html=True)


def page_comparateur(engine, market_df: pd.DataFrame):
    _maybe_demo("Comparateur")
    _header("Comparateur", "Comparer 2 à 3 idées produits pour préparer un rendez-vous")
    enriched = enrich_products_with_market(load_products(engine), market_df)
    names = enriched["nom"].tolist()
    selected = st.multiselect("Produits à comparer", names, default=names[:3], max_selections=3)
    comp = compare_products(enriched, selected)
    if comp.empty:
        st.info("Sélectionnez au moins un produit.")
        return

    c1, c2, c3 = st.columns(3)
    with c1: _kpi("Produits comparés", str(len(comp)), ACCENT)
    with c2: _kpi("Coupon max", f"{comp['coupon_annuel_pct'].max():.1f}%", GREEN)
    with c3: _kpi("Risque min", f"{int(comp['score_risque'].min())}/100", _risk_color(int(comp["score_risque"].min())))

    _download_csv("Exporter comparaison", comp, "comparaison_produits.csv")
    col_a, col_b = st.columns([1.15, 1])
    with col_a:
        _sec("COUPON VS SCORE RISQUE")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=comp["nom"], y=comp["coupon_annuel_pct"], name="Coupon (%)", marker_color=ACCENT))
        fig.add_trace(go.Bar(x=comp["nom"], y=comp["score_risque"], name="Score risque", marker_color=RED))
        _chart(fig, height=340)
        fig.update_layout(barmode="group", yaxis_title="Coupon / Score", xaxis_title="Produit")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col_b:
        _sec("RADAR COMMERCIAL")
        st.plotly_chart(_comparator_radar_fig(comp), use_container_width=True, config={"displayModeBar": False})

    col_table, col_profile = st.columns([1.1, 1])
    with col_table:
        _sec("TABLE DE DÉCISION")
        st.dataframe(comp, use_container_width=True, hide_index=True)
    with col_profile:
        _sec("PAYOFF DU PRODUIT SÉLECTIONNÉ")
        focus_name = st.selectbox("Produit focus", comp["nom"].tolist())
        focus = enriched[enriched["nom"] == focus_name].iloc[0]
        st.plotly_chart(_payoff_profile_fig(focus), use_container_width=True, config={"displayModeBar": False})


def page_dashboard_manager(engine, market_df: pd.DataFrame):
    _maybe_demo("Dashboard Manager")
    _header("Dashboard Manager", "Synthèse encours, risques et priorités commerciales")
    positions = load_positions(engine)
    enriched = enrich_products_with_market(load_products(engine), market_df)
    positions = positions.merge(enriched[["produit_id", "score_risque", "statut"]], on="produit_id", how="left")
    alerts = build_sales_alerts(load_positions(engine), enriched, market_df)
    encours = positions["nominal_souscrit"].sum()
    risk_encours = positions[positions["score_risque"] >= 60]["nominal_souscrit"].sum()
    c1, c2, c3, c4 = st.columns(4)
    with c1: _kpi("Encours total", f"{encours/1e6:.1f}M €", ACCENT)
    with c2: _kpi("Encours à risque", f"{risk_encours/1e3:.0f}k €", RED if risk_encours else GREEN)
    with c3: _kpi("Clients", str(positions["client_id"].nunique()), TEXT)
    with c4: _kpi("Alertes sales", str(len(alerts)), RED if len(alerts) else GREEN)

    col1, col2 = st.columns(2)
    with col1:
        _sec("ENCOURS PAR TYPE")
        by_type = positions.groupby("type_produit")["nominal_souscrit"].sum().reset_index()
        fig = go.Figure(go.Bar(
            x=[TYPE_LABEL.get(t, t) for t in by_type["type_produit"]],
            y=by_type["nominal_souscrit"] / 1000,
            marker_color=CHART_C[:len(by_type)],
            text=(by_type["nominal_souscrit"] / 1000).apply(lambda x: f"{x:.0f}k€"),
            textposition="outside",
        ))
        _chart(fig, height=320)
        fig.update_layout(showlegend=False, yaxis_title="k€")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with col2:
        _sec("TOP CLIENTS À RAPPELER")
        top = alerts.groupby("client").size().reset_index(name="alertes").sort_values("alertes", ascending=False).head(5) if not alerts.empty else pd.DataFrame(columns=["client", "alertes"])
        st.dataframe(top, use_container_width=True, hide_index=True)

    obs = upcoming_observations(enriched, days_ahead=30)
    if not obs.empty:
        _sec("PROCHAINES OBSERVATIONS — 30 JOURS")
        st.dataframe(
            obs[["nom", "sous_jacent_1", "date_obs", "jours", "score_risque"]],
            use_container_width=True, hide_index=True,
        )

    _sec("TOP PRODUITS À SURVEILLER")
    watch = enriched.sort_values("score_risque", ascending=False).head(5)
    for _, row in watch.iterrows():
        c_info, c_spark = st.columns([3, 1])
        with c_info:
            st.markdown(
                f"**{row['nom']}** · risque {int(_f(row.get('score_risque')))}/100 · "
                f"{_v(row.get('point_attention'), '')[:80]}",
            )
        with c_spark:
            sfig = _sparkline_fig(market_df, row["sous_jacent_1"], _risk_color(int(_f(row.get("score_risque")))))
            if sfig:
                st.plotly_chart(sfig, use_container_width=True, config={"displayModeBar": False})
