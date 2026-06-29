"""Pages Streamlit — Produits Structurés (v2)."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .analytics import (
    enrich_products_with_market,
    load_positions,
    load_products,
    simulate_autocall,
)

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
TYPE_LABEL   = {"autocall": "Autocall", "worst_of_autocall": "Worst-Of", "reverse_convertible": "Rev. Conv.", "capital_protected": "Cap. Protégé"}


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

def _score_bar(score: int) -> str:
    color = GREEN if score < 30 else (YELLOW if score < 60 else RED)
    return f"""
    <div style="width:100%;background:#1c2230;border-radius:4px;height:5px;overflow:hidden;">
      <div style="width:{score}%;background:{color};height:100%;border-radius:4px;"></div>
    </div>"""

def _header(title: str, sub: str):
    st.markdown(f'<div style="font-size:22px;font-weight:700;color:{TEXT};margin-bottom:3px;">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:13px;color:{MUTED};margin-bottom:20px;">{sub}</div>', unsafe_allow_html=True)


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

        jr   = _f(row.get("jours_restants"))
        jr_s = f"{int(jr)}j restants" if jr > 0 else _v(row.get("date_echeance",""))
        ki_html = _progress_bar(dist, row["statut"]) if row["type_produit"] != "capital_protected" else \
            f'<span style="color:{GREEN};font-size:12px;font-weight:600;">Capital 100% protégé à l\'échéance</span>'
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
              {_score_bar(score)}
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
              <div style="color:{MUTED};font-size:10px;margin-bottom:3px;">DIST. KI</div>
              <div style="color:{STATUT_COLOR.get(row['statut'],MUTED)};font-weight:700;">{"N/A" if row["type_produit"]=="capital_protected" else f"{dist:.1f}%"}</div>
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
            <div style="font-size:10px;color:{MUTED};margin-bottom:3px;">DISTANCE À LA BARRIÈRE KNOCK-IN</div>
            {ki_html}
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


# ── PAGE : Simulateur Autocall ────────────────────────────────────────────────
def page_simulateur(engine, market_df: pd.DataFrame):
    _header("Simulateur Autocall — Monte-Carlo",
            "Analyse probabiliste des scénarios, payoff et trajectoires")

    products  = load_products(engine)
    autocalls = products[products["type_produit"].isin(["autocall", "worst_of_autocall"])]
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
def page_clients(engine, market_df: pd.DataFrame):
    _header("Vue Clients", "Exposition par client, alertes risque et analyse de portefeuille")

    positions = load_positions(engine)
    enriched  = enrich_products_with_market(load_products(engine), market_df)
    if positions.empty:
        st.warning("Aucune position.")
        return

    positions = positions.merge(
        enriched[["produit_id", "statut", "dist_barriere_ki_pct", "worst_of_pct", "score_risque"]],
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
             {_score_bar(score_c)}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    for _, row in cp.sort_values("score_risque", ascending=False).iterrows():
        s_color = STATUT_COLOR.get(row.get("statut", "N/A"), MUTED)
        dist    = _f(row.get("dist_barriere_ki_pct"))
        sc      = int(_f(row.get("score_risque")))
        sc_c    = GREEN if sc < 30 else (YELLOW if sc < 60 else RED)

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
              {_score_bar(sc)}
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)


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
                reco = "Autocall ou Worst-Of — vol élevée = coupon attractif"
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
