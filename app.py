"""Application Streamlit — Finance de Marché."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "python"))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.db import init_database
from src.ui.theme import (
    ACCENT, BG, BG_CARD, BG_CARD2, BORDER, CHART_C,
    GREEN, MUTED, PURPLE, RED, TEXT, YELLOW, rgba,
)
from src.structured.pages import (
    page_alertes_sales, page_book_produits, page_comparateur,
    page_dashboard_manager, page_suivi_produits, page_simulateur,
    page_clients, page_screener, page_pitch_client, page_meeting_pack,
)
from src.ui.components import status_pill

# ── Config ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Entretien Tom Generali", page_icon="📈",
    layout="wide", initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html,body,[class*="css"]{{font-family:'Inter','Segoe UI',sans-serif;}}
.stApp{{background:{BG};color:{TEXT};}}

/* ── SIDEBAR ─────────────────────────────────────────────────────── */
[data-testid="stSidebar"]{{
  background:{BG} !important;
  border-right:1px solid {BORDER} !important;
}}
[data-testid="stSidebar"] *{{color:{TEXT} !important;}}

/* Tous les inputs sidebar */
[data-testid="stSidebar"] .stSelectbox>div>div,
[data-testid="stSidebar"] .stMultiSelect>div>div{{
  background:{BG_CARD} !important;
  border:1px solid {BORDER} !important;
  border-radius:6px !important;
  color:{TEXT} !important;
}}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stMultiSelect label,
[data-testid="stSidebar"] .stDateInput label{{
  color:{MUTED} !important;
  font-size:10px !important;
  font-weight:700 !important;
  text-transform:uppercase !important;
  letter-spacing:.07em !important;
}}
[data-testid="stSidebar"] span[data-baseweb="tag"]{{
  background:#1c2d42 !important;
  border:1px solid {ACCENT} !important;
  color:{ACCENT} !important;
  font-size:11px !important;
  border-radius:4px !important;
}}

/* ── NAVIGATION ─────────────────────────────────────────────────── */
[data-testid="stSidebar"] .stRadio>div{{gap:0 !important;}}
[data-testid="stSidebar"] .stRadio label{{
  display:flex !important; align-items:center !important;
  padding:9px 14px !important; border-radius:6px !important;
  margin:1px 6px !important; font-size:13px !important;
  font-weight:500 !important; color:{MUTED} !important;
  cursor:pointer !important; transition:all .15s !important;
}}
[data-testid="stSidebar"] .stRadio label:hover{{
  background:{BG_CARD} !important; color:{TEXT} !important;
}}
/* item sélectionné */
[data-testid="stSidebar"] .stRadio [aria-checked="true"] + div,
[data-testid="stSidebar"] .stRadio label[data-selected="true"]{{
  background:#1c2d42 !important; color:{ACCENT} !important;
  font-weight:700 !important;
}}
/* cacher le bouton rond */
[data-testid="stSidebar"] .stRadio input[type="radio"]{{display:none !important;}}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"]>label>div:first-child{{display:none !important;}}

/* items de séparation (headers nav) */
[data-testid="stSidebar"] .stRadio label:has(span[data-nav-header]){{
  cursor:default !important; padding:14px 14px 4px !important;
  font-size:10px !important; font-weight:700 !important;
  color:{MUTED} !important; text-transform:uppercase !important;
  letter-spacing:.1em !important; pointer-events:none !important;
  background:transparent !important;
}}

/* Bouton sidebar */
[data-testid="stSidebar"] .stButton>button{{
  width:100% !important; background:{BG_CARD} !important;
  border:1px solid {BORDER} !important; color:{MUTED} !important;
  border-radius:6px !important; font-size:12px !important;
  padding:8px !important; margin-top:4px !important;
}}
[data-testid="stSidebar"] .stButton>button:hover{{
  border-color:{ACCENT} !important; color:{ACCENT} !important;
}}

/* ── WIDGETS GLOBAL ──────────────────────────────────────────────── */
.stSelectbox>div>div,.stMultiSelect>div>div{{
  background:{BG_CARD2} !important; border:1px solid {BORDER} !important;
  border-radius:6px !important; color:{TEXT} !important;
}}
.stTabs [data-baseweb="tab"]{{
  background:transparent !important; color:{MUTED} !important;
  border-bottom:2px solid transparent !important; font-size:13px !important;
}}
.stTabs [aria-selected="true"]{{
  color:{ACCENT} !important; border-bottom:2px solid {ACCENT} !important;
  font-weight:600 !important;
}}
div[data-testid="metric-container"]{{
  background:{BG_CARD} !important; border:1px solid {BORDER} !important;
  border-radius:10px !important; padding:14px 18px !important;
}}
div[data-testid="metric-container"] label{{color:{MUTED} !important; font-size:11px !important;}}
div[data-testid="metric-container"] [data-testid="stMetricValue"]{{color:{TEXT} !important; font-size:22px !important;}}

/* ── KPI CARDS ───────────────────────────────────────────────────── */
.kpi-card{{
  background:{BG_CARD}; border:1px solid {BORDER}; border-radius:10px;
  padding:18px 20px 14px; min-height:88px;
}}
.kpi-label{{
  font-size:10px; color:{MUTED}; text-transform:uppercase;
  letter-spacing:.07em; margin-bottom:7px; font-weight:600;
}}
.kpi-value{{font-size:26px; font-weight:700; color:{TEXT}; line-height:1.1;}}
.kpi-delta-pos{{font-size:12px; color:{GREEN}; font-weight:600; margin-top:3px;}}
.kpi-delta-neg{{font-size:12px; color:{RED};   font-weight:600; margin-top:3px;}}
.kpi-delta-neu{{font-size:12px; color:{MUTED}; font-weight:600; margin-top:3px;}}

/* ── SECTIONS ────────────────────────────────────────────────────── */
.section-title{{
  font-size:11px; font-weight:700; color:{MUTED}; text-transform:uppercase;
  letter-spacing:.1em; margin:24px 0 12px; padding-bottom:6px;
  border-bottom:1px solid {BORDER};
}}
.page-header{{font-size:24px; font-weight:800; color:{TEXT}; margin-bottom:4px;}}
.page-sub{{font-size:13px; color:{MUTED}; margin-bottom:22px;}}

/* ── DATAFRAME ───────────────────────────────────────────────────── */
.stDataFrame{{border-radius:8px; overflow:hidden;}}
[data-testid="stDataFrame"] th{{
  background:{BG_CARD2} !important; color:{MUTED} !important;
  font-size:11px !important; font-weight:700 !important;
  text-transform:uppercase !important; letter-spacing:.06em !important;
}}
[data-testid="stDataFrame"] td{{
  background:{BG_CARD} !important; color:{TEXT} !important;
  font-size:12px !important;
}}

hr{{border-color:{BORDER} !important; margin:16px 0;}}
.js-plotly-plot .plotly{{background:transparent !important;}}

/* Enlever le padding par défaut du main content */
.main .block-container{{padding-top:2rem !important; max-width:1400px;}}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _rgba(hex_color: str, alpha: float = 0.15) -> str:
    return rgba(hex_color, alpha)


def kpi(label: str, value: str, delta: float | None = None, color: str = TEXT):
    if delta is None:
        d = ""
    elif delta > 0:
        d = f'<div class="kpi-delta-pos">▲ {delta:+.2f}%</div>'
    elif delta < 0:
        d = f'<div class="kpi-delta-neg">▼ {delta:.2f}%</div>'
    else:
        d = f'<div class="kpi-delta-neu">— 0.00%</div>'
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value" style="color:{color};">{value}</div>
      {d}
    </div>""", unsafe_allow_html=True)


def section(title: str):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


def page_header(title: str, subtitle: str = ""):
    st.markdown(f'<div class="page-header">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="page-sub">{subtitle}</div>', unsafe_allow_html=True)


def chart(fig: go.Figure, height: int = 400, **kw) -> go.Figure:
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=BG,
        font=dict(family="Inter, Segoe UI, sans-serif", color=MUTED, size=12),
        xaxis=dict(gridcolor=BORDER, zeroline=False, linecolor=BORDER, tickcolor=BORDER),
        yaxis=dict(gridcolor=BORDER, zeroline=False, linecolor=BORDER, tickcolor=BORDER),
        margin=dict(l=10, r=10, t=28, b=10),
        legend=dict(
            bgcolor="rgba(0,0,0,0)", bordercolor=BORDER,
            font=dict(size=11, color=MUTED), orientation="h", y=-0.18,
        ),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=BG_CARD2, bordercolor=BORDER, font=dict(color=TEXT, size=12)),
        **kw,
    )
    return fig


# ── DB ────────────────────────────────────────────────────────────────────────
def _set_meta(engine, **values) -> None:
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS app_metadata (key TEXT PRIMARY KEY, value TEXT)"))
        for key, value in values.items():
            conn.execute(
                text("""
                    INSERT INTO app_metadata (key, value)
                    VALUES (:key, :value)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """),
                {"key": key, "value": "" if value is None else str(value)},
            )


def _get_meta(engine) -> dict[str, str]:
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS app_metadata (key TEXT PRIMARY KEY, value TEXT)"))
        rows = conn.execute(text("SELECT key, value FROM app_metadata")).fetchall()
    return {r[0]: r[1] for r in rows}


@st.cache_resource(show_spinner=False)
def get_db():
    engine = init_database()
    from sqlalchemy import text

    with engine.connect() as conn:
        n        = conn.execute(text("SELECT COUNT(*) FROM fact_prix")).scalar()
        last_row = conn.execute(text("SELECT MAX(date_cours) FROM fact_prix")).scalar()

    # Au démarrage, ne jamais bloquer l'interface sur Yahoo Finance.
    # Si la base est vide, on seed immédiatement en données demo.
    # Le bouton "Rafraîchir" tente Yahoo Finance explicitement.
    last_date  = pd.to_datetime(last_row).date() if last_row else None

    if n == 0:
        from src.load_to_sql import load_prices
        from src.ingest.generate_demo_data import generate_demo_data
        load_prices(engine, generate_demo_data(days=500))
        _set_meta(
            engine,
            data_source="Données démo",
            data_message="Démarrage rapide local : données démo. Utilisez Rafraîchir pour tenter Yahoo Finance.",
            loaded_tickers="demo",
            failed_tickers="",
            last_refresh=str(pd.Timestamp.today().date()),
        )
    elif last_date is not None:
        meta = _get_meta(engine)
        if not meta.get("data_source"):
            _set_meta(
                engine,
                data_source="Base locale",
                data_message="Données déjà présentes en base locale.",
                loaded_tickers="",
                failed_tickers="",
                last_refresh=str(last_date),
            )
    return engine


@st.cache_data(ttl=300, show_spinner=False)
def load_data() -> pd.DataFrame:
    engine = get_db()
    with engine.connect() as conn:
        df = pd.read_sql("SELECT * FROM vw_dashboard_marche", conn)
    df["date_cours"] = pd.to_datetime(df["date_cours"])
    return df


def ensure_data(df: pd.DataFrame) -> pd.DataFrame:
    if not df.empty:
        return df
    with st.spinner("Génération des données demo…"):
        from src.ingest.generate_demo_data import generate_demo_data
        from src.load_to_sql import load_prices
        load_prices(get_db(), generate_demo_data(days=500))
        st.cache_data.clear()
    return load_data()


def data_quality(df: pd.DataFrame, engine) -> dict[str, object]:
    from datetime import timedelta
    meta = _get_meta(engine)
    if df.empty:
        return {**meta, "rows": 0, "last_date": "N/A", "tickers": 0, "stale": True, "last_refresh": meta.get("last_refresh", "N/A")}
    last_date = df["date_cours"].max().date()
    stale = last_date < (pd.Timestamp.today().date() - timedelta(days=1))
    return {
        **meta,
        "rows": int(len(df)),
        "last_date": str(last_date),
        "tickers": int(df["ticker"].nunique()),
        "stale": bool(stale),
        "last_refresh": meta.get("last_refresh", str(last_date)),
    }


def data_quality_banner(info: dict[str, object]):
    source = str(info.get("data_source", "Source inconnue"))
    stale = bool(info.get("stale"))
    if source == "Yahoo Finance" and not stale:
        color, pill = GREEN, "LIVE"
    elif source == "Données démo":
        color, pill = YELLOW, "DEMO"
    elif stale:
        color, pill = RED, "STALE"
    else:
        color, pill = YELLOW, "LOCAL"
    msg = info.get("data_message", "")
    pill_html = status_pill(pill, color)
    st.markdown(f"""
    <div style="background:{BG_CARD};border:1px solid {BORDER};border-left:3px solid {color};
                border-radius:9px;padding:10px 14px;margin-bottom:16px;font-size:12px;">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;">
        <span style="color:{color};font-weight:700;">Données : {source}</span>
        {pill_html}
      </div>
      <span style="color:{MUTED};"> · Dernière séance : {info.get('last_date','N/A')} · Dernier refresh : {info.get('last_refresh','N/A')} · {info.get('tickers',0)} tickers</span>
      <div style="color:{MUTED};margin-top:3px;">{msg}</div>
    </div>
    """, unsafe_allow_html=True)


def try_auto_refresh(df: pd.DataFrame, engine) -> None:
    """Tente un refresh Yahoo au démarrage si les cours sont obsolètes (non bloquant)."""
    if st.session_state.get("auto_refresh_tried"):
        return
    st.session_state["auto_refresh_tried"] = True
    meta = _get_meta(engine)
    if meta.get("data_source") == "Données démo" or df.empty:
        return
    last_date = pd.to_datetime(df["date_cours"].max()).date()
    if last_date >= pd.Timestamp.today().date() - pd.Timedelta(days=1):
        return
    try:
        from src.load_to_sql import load_prices
        from src.ingest.fetch_yfinance import fetch_market_data, get_last_fetch_status
        new_df = fetch_market_data()
        if new_df.empty:
            return
        load_prices(engine, new_df)
        status = get_last_fetch_status()
        _set_meta(
            engine,
            data_source="Yahoo Finance",
            data_message=status.get("message", "Auto-refresh Yahoo Finance OK"),
            loaded_tickers=",".join(status.get("loaded_tickers", [])),
            failed_tickers=",".join(status.get("failed_tickers", [])),
            last_refresh=str(status.get("latest_date") or pd.Timestamp.today().date()),
        )
        st.cache_data.clear()
    except Exception:
        pass


# ── Navigation ────────────────────────────────────────────────────────────────
_NAV_ITEMS = [
    ("page",   "Accueil"),
    ("header", "── Marchés"),
    ("page",   "Vue Marché"),
    ("page",   "Risque & Indicateurs"),
    ("page",   "Corrélations"),
    ("page",   "Bougies"),
    ("header", "── Produits Structurés"),
    ("page",   "Book Produits"),
    ("page",   "Alertes Sales"),
    ("page",   "Dashboard Manager"),
    ("page",   "Comparateur"),
    ("page",   "Suivi Produits"),
    ("page",   "Simulateur Autocall"),
    ("page",   "Vue Clients"),
    ("page",   "Pitch Client"),
    ("page",   "Meeting Pack"),
    ("page",   "Screener"),
]

_PAGE_LABELS = [item[1] for item in _NAV_ITEMS if item[0] == "page"]
_ALL_LABELS  = [item[1] for item in _NAV_ITEMS]
_PAGE_NAMES  = {lbl: lbl.split("  ", 1)[-1] for lbl in _ALL_LABELS}
_NAME_REMAP  = {
    "Suivi Produits": "Suivi Produits Structurés",
    "Screener":       "Screener Sous-jacents",
}

# Valeurs par défaut session
for _k, _v in [("nav_sel", "Accueil"), ("nav_prev", "Accueil"), ("demo_mode", False), ("demo_step", 0)]:
    if _k not in st.session_state:
        st.session_state[_k] = _v


def sidebar(df: pd.DataFrame):
    sb = st.sidebar
    engine = get_db()
    info = data_quality(df, engine)

    sb.markdown(f"""
    <div style="padding:22px 18px 14px;border-bottom:1px solid {BORDER};margin-bottom:10px;">
      <div style="font-size:17px;font-weight:800;color:{ACCENT};letter-spacing:-.02em;line-height:1.2;">Entretien Tom</div>
      <div style="font-size:13px;font-weight:700;color:{TEXT};margin-top:1px;">Generali</div>
      <div style="font-size:10px;color:{MUTED};margin-top:2px;">Finance de Marché · Produits Structurés</div>
    </div>""", unsafe_allow_html=True)

    source_color = GREEN if info.get("data_source") == "Yahoo Finance" and not info.get("stale") else YELLOW
    if info.get("stale"):
        source_color = RED
    sb.markdown(f"""
    <div style="margin:0 10px 12px;background:{BG_CARD};border:1px solid {BORDER};border-left:3px solid {source_color};
                border-radius:8px;padding:9px 10px;font-size:11px;">
      <div style="color:{source_color};font-weight:700;">{info.get('data_source','Source inconnue')}</div>
      <div style="color:{MUTED};margin-top:2px;">Séance : {info.get('last_date','N/A')}</div>
      <div style="color:{MUTED};">Refresh : {info.get('last_refresh','N/A')}</div>
      <div style="color:{MUTED};">{info.get('tickers',0)} tickers · {info.get('rows',0)} lignes</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Filtres ──
    sb.markdown(f'<div style="padding:0 10px 4px;font-size:10px;font-weight:700;color:{MUTED};text-transform:uppercase;letter-spacing:.08em;">Filtres marché</div>', unsafe_allow_html=True)
    types = ["Tous"] + sorted(df["type_instrument"].dropna().unique())
    t = sb.selectbox("Type d'instrument", types, label_visibility="visible")
    filtered = df if t == "Tous" else df[df["type_instrument"] == t]
    tickers = sorted(filtered["ticker"].unique())
    sel = sb.multiselect("Instruments", tickers, default=tickers[:6])
    min_d, max_d = df["date_cours"].min().date(), df["date_cours"].max().date()
    dr = sb.date_input("Période", value=(min_d, max_d), min_value=min_d, max_value=max_d)

    sb.markdown(f'<hr style="border-color:{BORDER};margin:12px 0;"/>', unsafe_allow_html=True)

    # ── Navigation unique ──
    nav_index = _ALL_LABELS.index(st.session_state["nav_sel"]) if st.session_state["nav_sel"] in _ALL_LABELS else 0
    chosen = sb.radio("navigation", _ALL_LABELS, label_visibility="collapsed", index=nav_index)

    # Si l'utilisateur clique sur un header → on garde la page précédente
    if _NAV_ITEMS[_ALL_LABELS.index(chosen)][0] == "header":
        chosen = st.session_state["nav_prev"]
    else:
        st.session_state["nav_prev"] = chosen
    st.session_state["nav_sel"] = chosen

    raw  = _PAGE_NAMES.get(chosen, chosen)
    page = _NAME_REMAP.get(raw, raw)

    sb.markdown(f'<hr style="border-color:{BORDER};margin:12px 0 8px;"/>', unsafe_allow_html=True)
    if sb.button("Rafraîchir les données"):
        from src.load_to_sql import load_prices
        with st.spinner("Téléchargement Yahoo Finance…"):
            try:
                from src.ingest.fetch_yfinance import fetch_market_data, get_last_fetch_status
                df = fetch_market_data()
                if df.empty:
                    raise ValueError("vide")
                engine = get_db()
                load_prices(engine, df)
                status = get_last_fetch_status()
                failed = status.get("failed_tickers", [])
                if failed:
                    st.sidebar.warning(f"Tickers en échec : {', '.join(failed)}")
                _set_meta(
                    engine,
                    data_source="Yahoo Finance",
                    data_message=status.get("message", "Yahoo Finance OK"),
                    loaded_tickers=",".join(status.get("loaded_tickers", [])),
                    failed_tickers=",".join(status.get("failed_tickers", [])),
                    last_refresh=str(status.get("latest_date") or pd.Timestamp.today().date()),
                )
            except Exception as exc:
                from src.ingest.generate_demo_data import generate_demo_data
                engine = get_db()
                load_prices(engine, generate_demo_data(days=500))
                _set_meta(
                    engine,
                    data_source="Données démo",
                    data_message=f"Fallback démo utilisé: {exc}",
                    loaded_tickers="demo",
                    failed_tickers="",
                    last_refresh=str(pd.Timestamp.today().date()),
                )
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

    return sel, dr, page


def filter_df(df, tickers, dr):
    mask = df["ticker"].isin(tickers)
    if isinstance(dr, (list, tuple)) and len(dr) == 2:
        mask &= (df["date_cours"] >= pd.Timestamp(dr[0])) & \
                (df["date_cours"] <= pd.Timestamp(dr[1]))
    return df[mask].sort_values(["ticker", "date_cours"])


# ── PAGE : Accueil ────────────────────────────────────────────────────────────
def page_accueil(df: pd.DataFrame, engine):
    page_header("Entretien Tom Generali", "Démonstrateur Python, SQL et Streamlit pour assistant sales produits structurés")
    info = data_quality(df, engine)
    data_quality_banner(info)

    from src.structured.analytics import build_sales_alerts, enrich_products_with_market, load_positions, load_products
    positions = load_positions(engine)
    products = load_products(engine)
    enriched = enrich_products_with_market(products, df) if not products.empty else products
    alerts = build_sales_alerts(positions, enriched, df) if not enriched.empty else pd.DataFrame()

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi("Source data", str(info.get("data_source", "N/A")), color=GREEN if info.get("data_source") == "Yahoo Finance" and not info.get("stale") else YELLOW)
    with c2: kpi("Dernière séance", str(info.get("last_date", "N/A")))
    with c3: kpi("Alertes sales", str(len(alerts)), color=RED if len(alerts) else GREEN)
    with c4: kpi("Tickers", str(info.get("tickers", 0)), color=ACCENT)

    section("PARCOURS DÉMO ENTRETIEN (5 MIN)")
    st.markdown(f"""
    <div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:10px;padding:14px 18px;margin-bottom:12px;color:{TEXT};font-size:13px;line-height:1.6;">
      Parcours guidé : Meeting Pack → Comparateur → Book Produits → Dashboard Manager → Export HTML.
    </div>
    """, unsafe_allow_html=True)
    bc1, bc2, bc3, bc4, bc5 = st.columns(5)
    demo_pages = ["Meeting Pack", "Comparateur", "Book Produits", "Dashboard Manager", "Meeting Pack"]
    for col, (step, label) in zip([bc1, bc2, bc3, bc4, bc5], enumerate(demo_pages)):
        with col:
            if st.button(label, key=f"demo_nav_{step}", use_container_width=True):
                st.session_state["demo_mode"] = True
                st.session_state["demo_step"] = step
                st.session_state["nav_sel"] = label
                st.rerun()
    if st.button("Démarrer la démo entretien", type="primary"):
        st.session_state["demo_mode"] = True
        st.session_state["demo_step"] = 0
        st.session_state["nav_sel"] = "Meeting Pack"
        st.rerun()

    if not alerts.empty:
        section("ALERTES PRIORITAIRES")
        for _, row in alerts.head(3).iterrows():
            color = RED if row["priorite"] == "Haute" else YELLOW
            st.markdown(f"""
            <div style="background:{BG_CARD};border:1px solid {BORDER};border-left:3px solid {color};border-radius:8px;padding:10px 14px;margin-bottom:8px;font-size:12px;">
              <span style="color:{color};font-weight:700;">{row['priorite']}</span>
              <span style="color:{TEXT};font-weight:600;"> · {row['client']} — {row['produit']}</span>
              <div style="color:{MUTED};margin-top:3px;">{row['raison'][:120]}</div>
            </div>
            """, unsafe_allow_html=True)

    section("CE QUE DÉMONTRE LE PROJET")
    st.markdown(f"""
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:16px;">
      <div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:10px;padding:16px;">
        <div style="color:{ACCENT};font-weight:800;margin-bottom:7px;">Python</div>
        <div style="color:{TEXT};font-size:13px;line-height:1.5;">Ingestion Yahoo Finance, fallback démo, indicateurs techniques, simulation Monte-Carlo et scoring produits.</div>
      </div>
      <div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:10px;padding:16px;">
        <div style="color:{GREEN};font-weight:800;margin-bottom:7px;">SQL</div>
        <div style="color:{TEXT};font-size:13px;line-height:1.5;">Base SQLite structurée : instruments, prix, indicateurs, clients, positions et catalogue de produits structurés.</div>
      </div>
      <div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:10px;padding:16px;">
        <div style="color:{YELLOW};font-weight:800;margin-bottom:7px;">Streamlit</div>
        <div style="color:{TEXT};font-size:13px;line-height:1.5;">Interface sales : suivi marché, alertes produits, pitch client, exports et mise en ligne cloud.</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    section("FLUX DE DONNÉES")
    st.markdown(f"""
    <div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:10px;padding:16px 18px;font-size:13px;color:{TEXT};line-height:1.7;">
      Yahoo Finance → Python Pipeline → SQLite → Analytics produits → Streamlit → Assistant Sales<br>
      <span style="color:{MUTED};">Si Yahoo Finance échoue, l'application bascule automatiquement vers des données démo et l'indique clairement.</span>
    </div>
    """, unsafe_allow_html=True)

    section("QUALITÉ DES DONNÉES")
    meta_loaded = [x for x in str(info.get("loaded_tickers", "")).split(",") if x]
    meta_failed = [x for x in str(info.get("failed_tickers", "")).split(",") if x]
    latest = (
        df.sort_values("date_cours")
        .groupby("ticker")
        .last()
        .reset_index()[["ticker", "date_cours", "close", "rendement_jour"]]
        .copy()
    )
    latest["rendement_jour"] = (latest["rendement_jour"] * 100).round(2)
    latest.columns = ["Ticker", "Dernière date", "Dernier cours", "Rend. jour (%)"]
    c_quality, c_status = st.columns([3, 2])
    with c_quality:
        st.dataframe(latest, use_container_width=True, hide_index=True)
    with c_status:
        st.markdown(f"""
        <div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:10px;padding:14px 16px;font-size:12px;line-height:1.6;">
          <div style="color:{GREEN};font-weight:700;margin-bottom:5px;">Tickers chargés</div>
          <div style="color:{TEXT};">{", ".join(meta_loaded) if meta_loaded else "Non renseigné"}</div>
          <div style="color:{RED};font-weight:700;margin:12px 0 5px;">Tickers échoués</div>
          <div style="color:{TEXT};">{", ".join(meta_failed) if meta_failed else "Aucun"}</div>
        </div>
        """, unsafe_allow_html=True)

    section("PAGES CLÉS")
    st.markdown(f"""
    <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:12px;">
      <div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;padding:13px;color:{TEXT};font-size:13px;">Book Produits : recherche, fiche détaillée, pitch 30 secondes et stress tests.</div>
      <div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;padding:13px;color:{TEXT};font-size:13px;">Alertes Sales : clients à appeler, raisons et actions recommandées.</div>
      <div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;padding:13px;color:{TEXT};font-size:13px;">Meeting Pack : support rendez-vous client avec visuels, alertes, idée produit, payoff et pitch.</div>
      <div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;padding:13px;color:{TEXT};font-size:13px;">Suivi Produits : barrières, CLN, risques et actions sales.</div>
      <div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;padding:13px;color:{TEXT};font-size:13px;">Pitch Client : adéquation produit-profil, recommandations et exports.</div>
      <div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;padding:13px;color:{TEXT};font-size:13px;">Screener : idées produits selon volatilité, RSI et tendance.</div>
    </div>
    """, unsafe_allow_html=True)

    section("PARCOURS DÉMO ENTRETIEN")
    st.markdown(f"""
    <div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:10px;padding:16px 18px;color:{TEXT};font-size:13px;line-height:1.7;">
      <b style="color:{ACCENT};">1. Meeting Pack</b> : fiche rendez-vous complète + export HTML.<br>
      <b style="color:{ACCENT};">2. Comparateur</b> : radar et payoff pour argumenter.<br>
      <b style="color:{ACCENT};">3. Book Produits</b> : stress tests et barrières vs sous-jacent.<br>
      <b style="color:{ACCENT};">4. Dashboard Manager</b> : encours, alertes, observations à venir.<br>
      <span style="color:{MUTED};">Phrase entretien : « J'ai voulu relier la donnée marché, la base SQL et le besoin concret d'un assistant sales : prioriser, expliquer et préparer un échange client. »</span>
    </div>
    """, unsafe_allow_html=True)


# ── PAGE : Vue Marché ─────────────────────────────────────────────────────────
def page_marche(df: pd.DataFrame):
    page_header("Vue Marché", "Cours normalisés, rendements cumulés et résumé des actifs")

    last = df.sort_values("date_cours").groupby("ticker").last().reset_index()

    # KPI par actif
    cols = st.columns(min(len(last), 5))
    for i, (_, r) in enumerate(last.head(5).iterrows()):
        delta = float(r.get("rendement_jour") or 0) * 100
        with cols[i]:
            kpi(r["ticker"], f"{r['close']:,.1f}", delta)

    st.markdown("<br>", unsafe_allow_html=True)
    section("PERFORMANCE NORMALISÉE (BASE 100)")

    fig = go.Figure()
    for i, (ticker, grp) in enumerate(df.groupby("ticker")):
        base = grp["close"].iloc[0]
        if base and base != 0:
            fig.add_trace(go.Scatter(
                x=grp["date_cours"],
                y=(grp["close"] / base * 100).round(3),
                name=ticker, mode="lines",
                line=dict(color=CHART_C[i % len(CHART_C)], width=2),
                hovertemplate=f"<b>{ticker}</b>: %{{y:.1f}}<extra></extra>",
            ))
    chart(fig, height=400)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    col1, col2 = st.columns(2)

    with col1:
        section("DISTRIBUTION DES RENDEMENTS JOURNALIERS")
        fig2 = go.Figure()
        for i, (ticker, grp) in enumerate(df.dropna(subset=["rendement_jour"]).groupby("ticker")):
            c = CHART_C[i % len(CHART_C)]
            fig2.add_trace(go.Box(
                y=(grp["rendement_jour"] * 100).round(3),
                name=ticker, marker_color=c, line_color=c,
                fillcolor=_rgba(c, 0.18), boxpoints=False,
            ))
        chart(fig2, height=320)
        fig2.update_layout(showlegend=False, yaxis_title="Rendement (%)")
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    with col2:
        section("RENDEMENT CUMULÉ SUR LA PÉRIODE")
        perf_rows = []
        for ticker, grp in df.groupby("ticker"):
            if len(grp) >= 2:
                r = (grp["close"].iloc[-1] / grp["close"].iloc[0] - 1) * 100
                perf_rows.append({"ticker": ticker, "rendement": round(r, 2)})
        perf_df = pd.DataFrame(perf_rows).sort_values("rendement", ascending=True)
        colors  = [GREEN if v >= 0 else RED for v in perf_df["rendement"]]
        fig3 = go.Figure(go.Bar(
            x=perf_df["rendement"], y=perf_df["ticker"],
            orientation="h", marker_color=colors,
            text=perf_df["rendement"].apply(lambda x: f"{x:+.1f}%"),
            textposition="outside", textfont=dict(size=11, color=TEXT),
        ))
        fig3.add_vline(x=0, line_color=BORDER, line_width=1)
        chart(fig3, height=320)
        fig3.update_layout(showlegend=False, xaxis_title="Rendement (%)")
        st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})

    section("DERNIERS COURS")
    cols_disp = ["ticker", "nom", "type_instrument", "secteur", "close", "rendement_jour"]
    cols_disp = [c for c in cols_disp if c in last.columns]
    display = last[cols_disp].copy()
    if "rendement_jour" in display.columns:
        display["rendement_jour"] = (display["rendement_jour"] * 100).round(2)
    rename = {"ticker": "Ticker", "nom": "Nom", "type_instrument": "Type",
               "secteur": "Secteur", "close": "Clôture", "rendement_jour": "Rend. J (%)"}
    display.columns = [rename.get(c, c) for c in display.columns]
    st.dataframe(display, use_container_width=True, hide_index=True)


# ── PAGE : Risque ─────────────────────────────────────────────────────────────
def page_risque(df: pd.DataFrame):
    page_header("Risque & Indicateurs Techniques",
                "Volatilité annualisée, RSI, SMA50 et signaux de marché")

    last = df.sort_values("date_cours").groupby("ticker").last().reset_index()

    avg_vol   = last["volatilite_20j"].dropna().mean() * (252**0.5) * 100
    avg_rsi   = last["rsi_14"].dropna().mean()
    above_sma = (last["signal_tendance"] == "Au-dessus SMA50").sum()
    total_sig = len(last.dropna(subset=["signal_tendance"]))

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi("Volatilité moy. ann.", f"{avg_vol:.1f}%")
    with c2: kpi("RSI moyen (14j)", f"{avg_rsi:.1f}")
    with c3: kpi("Au-dessus SMA50", f"{above_sma}/{total_sig}", color=GREEN if above_sma > total_sig/2 else RED)
    with c4:
        bullish = (last["rsi_14"] > 50).sum()
        tot_rsi = len(last.dropna(subset=["rsi_14"]))
        kpi("RSI > 50 (haussier)", f"{bullish}/{tot_rsi}", color=GREEN if bullish > tot_rsi/2 else RED)

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        section("VOLATILITÉ ANNUALISÉE (20J)")
        vol_df = last.dropna(subset=["volatilite_20j"]).copy()
        vol_df["vol_ann"] = (vol_df["volatilite_20j"] * (252**0.5) * 100).round(2)
        vol_df = vol_df.sort_values("vol_ann", ascending=True)
        bar_c  = [RED if v > 30 else YELLOW if v > 20 else GREEN for v in vol_df["vol_ann"]]
        fig = go.Figure(go.Bar(
            x=vol_df["vol_ann"], y=vol_df["ticker"], orientation="h",
            marker_color=bar_c,
            text=vol_df["vol_ann"].apply(lambda x: f"{x:.1f}%"),
            textposition="outside", textfont=dict(size=11, color=TEXT),
        ))
        chart(fig, height=340)
        fig.update_layout(showlegend=False, xaxis_title="Volatilité ann. (%)")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col2:
        section("RSI 14 JOURS")
        rsi_df = last.dropna(subset=["rsi_14"]).sort_values("rsi_14", ascending=True)
        bar_rsi= [RED if v >= 70 else GREEN if v <= 30 else ACCENT for v in rsi_df["rsi_14"]]
        fig2 = go.Figure(go.Bar(
            x=rsi_df["rsi_14"].round(1), y=rsi_df["ticker"], orientation="h",
            marker_color=bar_rsi,
            text=rsi_df["rsi_14"].round(1).astype(str),
            textposition="outside", textfont=dict(size=11, color=TEXT),
        ))
        fig2.add_vline(x=70, line_dash="dash", line_color=RED,   line_width=1.2,
                       annotation_text="Surachat", annotation_font_color=RED,   annotation_font_size=10)
        fig2.add_vline(x=30, line_dash="dash", line_color=GREEN, line_width=1.2,
                       annotation_text="Survente", annotation_font_color=GREEN, annotation_font_size=10)
        chart(fig2, height=340)
        fig2.update_layout(showlegend=False, xaxis_title="RSI", xaxis_range=[0, 115])
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    section("VOLATILITÉ GLISSANTE ANNUALISÉE (20J)")
    vol_roll = df.dropna(subset=["volatilite_20j"]).copy()
    vol_roll["vol_ann"] = vol_roll["volatilite_20j"] * (252**0.5) * 100
    fig3 = go.Figure()
    for i, (ticker, grp) in enumerate(vol_roll.groupby("ticker")):
        fig3.add_trace(go.Scatter(
            x=grp["date_cours"], y=grp["vol_ann"].round(2),
            name=ticker, mode="lines",
            line=dict(color=CHART_C[i % len(CHART_C)], width=1.8),
        ))
    chart(fig3, height=340)
    fig3.update_layout(yaxis_title="Volatilité ann. (%)")
    st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})

    section("ÉCART COURS / SMA50")
    sma_df = last.dropna(subset=["sma_50"]).copy()
    sma_df["ecart"] = ((sma_df["close"] / sma_df["sma_50"]) - 1) * 100
    sma_df = sma_df.sort_values("ecart")
    c4 = [GREEN if v >= 0 else RED for v in sma_df["ecart"]]
    fig4 = go.Figure(go.Bar(
        x=sma_df["ticker"], y=sma_df["ecart"].round(2),
        marker_color=c4,
        text=sma_df["ecart"].round(1).apply(lambda x: f"{x:+.1f}%"),
        textposition="outside", textfont=dict(size=11, color=TEXT),
    ))
    fig4.add_hline(y=0, line_color=BORDER, line_width=1)
    chart(fig4, height=300)
    fig4.update_layout(showlegend=False, yaxis_title="Écart vs SMA50 (%)")
    st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar": False})


# ── PAGE : Corrélations ───────────────────────────────────────────────────────
def page_correlations(df: pd.DataFrame):
    page_header("Matrice de Corrélations",
                "Coefficients de corrélation des rendements quotidiens entre actifs")

    if df["ticker"].nunique() < 2:
        st.warning("Sélectionnez au moins 2 instruments dans le filtre pour calculer les corrélations.")
        return

    pivot = (
        df.dropna(subset=["rendement_jour"])
        .pivot_table(index="date_cours", columns="ticker", values="rendement_jour")
        .dropna(how="all")
    )
    if pivot.shape[1] < 2:
        st.warning("Pas assez de données communes pour calculer les corrélations.")
        return

    corr = pivot.corr().round(3)

    section("HEATMAP DE CORRÉLATION")
    text_m = [[f"{v:.2f}" for v in row] for row in corr.values]
    fig = go.Figure(go.Heatmap(
        z=corr.values,
        x=corr.columns.tolist(),
        y=corr.index.tolist(),
        colorscale=[[0.0, RED], [0.5, BG_CARD2], [1.0, GREEN]],
        zmid=0, zmin=-1, zmax=1,
        text=text_m, texttemplate="%{text}",
        textfont=dict(size=12, color=TEXT),
        colorbar=dict(
            title=dict(text="Corrélation", font=dict(color=MUTED, size=11)),
            tickfont=dict(color=MUTED, size=10),
            len=0.9,
        ),
        hoverongaps=False,
        hovertemplate="<b>%{x}</b> × <b>%{y}</b><br>Corrélation: <b>%{z:.3f}</b><extra></extra>",
    ))
    fig.update_layout(
        height=500,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=BG_CARD,
        font=dict(color=MUTED, size=12),
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis=dict(tickfont=dict(size=11, color=MUTED), linecolor=BORDER, side="bottom"),
        yaxis=dict(tickfont=dict(size=11, color=MUTED), linecolor=BORDER, autorange="reversed"),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # Paires
    corr_flat = corr.copy()
    corr_flat.index.name   = "Ticker A"
    corr_flat.columns.name = "Ticker B"
    pairs = corr_flat.stack().reset_index()
    pairs.columns = ["Ticker A", "Ticker B", "Corrélation"]
    pairs = pairs[pairs["Ticker A"] < pairs["Ticker B"]].sort_values("Corrélation", ascending=False)

    col1, col2 = st.columns(2)
    with col1:
        section("TOP 5 — CORRÉLATION POSITIVE")
        top5 = pairs.head(5).copy()
        top5["Corrélation"] = top5["Corrélation"].apply(lambda x: f"{x:.3f}")
        st.dataframe(top5, use_container_width=True, hide_index=True)
    with col2:
        section("TOP 5 — CORRÉLATION NÉGATIVE (DIVERSIFICATION)")
        bot5 = pairs.tail(5).iloc[::-1].copy()
        bot5["Corrélation"] = bot5["Corrélation"].apply(lambda x: f"{x:.3f}")
        st.dataframe(bot5, use_container_width=True, hide_index=True)

    # Corrélation glissante
    section("CORRÉLATION GLISSANTE 60J ENTRE DEUX ACTIFS")
    tickers = sorted(df["ticker"].unique())
    cc1, cc2 = st.columns(2)
    ta = cc1.selectbox("Actif A", tickers, index=0)
    tb = cc2.selectbox("Actif B", tickers, index=min(1, len(tickers)-1))
    if ta != tb:
        pa = df[df["ticker"] == ta].set_index("date_cours")["rendement_jour"].dropna()
        pb = df[df["ticker"] == tb].set_index("date_cours")["rendement_jour"].dropna()
        common = pa.index.intersection(pb.index)
        if len(common) >= 60:
            roll = pa.loc[common].rolling(60).corr(pb.loc[common]).dropna().reset_index()
            roll.columns = ["date_cours", "correlation"]
            fig5 = go.Figure()
            fig5.add_trace(go.Scatter(
                x=roll["date_cours"], y=roll["correlation"].round(3),
                mode="lines", fill="tozeroy",
                line=dict(color=ACCENT, width=2),
                fillcolor=_rgba(ACCENT, 0.12),
                name="Corrélation 60j",
                hovertemplate="<b>%{x|%d/%m/%y}</b>: %{y:.3f}<extra></extra>",
            ))
            fig5.add_hline(y=0,    line_color=BORDER, line_width=1)
            fig5.add_hline(y=0.7,  line_color=RED,    line_dash="dot", line_width=1,
                           annotation_text="Forte corrélation", annotation_font_color=RED, annotation_font_size=10)
            fig5.add_hline(y=-0.7, line_color=GREEN,  line_dash="dot", line_width=1,
                           annotation_text="Diversification", annotation_font_color=GREEN, annotation_font_size=10)
            chart(fig5, height=320)
            fig5.update_layout(
                yaxis=dict(range=[-1.1, 1.1], title="Corrélation"),
                title=dict(text=f"{ta}  ×  {tb}", font=dict(color=TEXT, size=14)),
                showlegend=False,
            )
            st.plotly_chart(fig5, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info(f"Pas assez de données communes entre {ta} et {tb} (minimum 60 jours).")
    else:
        st.info("Sélectionnez deux actifs différents.")


# ── PAGE : Bougies ────────────────────────────────────────────────────────────
def page_bougie(df: pd.DataFrame):
    page_header("Graphique en Bougies", "OHLCV avec moyennes mobiles SMA20 / SMA50")

    tickers = sorted(df["ticker"].unique())
    col1, col2, col3 = st.columns([2, 1, 1])
    ticker = col1.selectbox("Instrument", tickers)
    grp    = df[df["ticker"] == ticker].sort_values("date_cours")

    last = grp.iloc[-1]
    rend = float(last.get("rendement_jour") or 0) * 100
    vol  = float(last.get("volatilite_20j") or 0) * (252**0.5) * 100
    with col2: kpi("Dernier cours", f"{last['close']:,.2f}", rend)
    with col3: kpi("Vol. ann. (20j)", f"{vol:.1f}%")

    st.markdown("<br>", unsafe_allow_html=True)
    section("OHLCV + MOYENNES MOBILES")

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=grp["date_cours"],
        open=grp["open"], high=grp["high"],
        low=grp["low"], close=grp["close"],
        name="OHLC",
        increasing=dict(line=dict(color=GREEN), fillcolor=_rgba(GREEN, 0.75)),
        decreasing=dict(line=dict(color=RED),   fillcolor=_rgba(RED,   0.75)),
    ))
    if "sma_20" in grp.columns and grp["sma_20"].notna().any():
        fig.add_trace(go.Scatter(
            x=grp["date_cours"], y=grp["sma_20"],
            name="SMA 20", mode="lines",
            line=dict(color=YELLOW, width=1.5, dash="dot"),
        ))
    if "sma_50" in grp.columns and grp["sma_50"].notna().any():
        fig.add_trace(go.Scatter(
            x=grp["date_cours"], y=grp["sma_50"],
            name="SMA 50", mode="lines",
            line=dict(color=PURPLE, width=1.8),
        ))
    chart(fig, height=460)
    fig.update_layout(xaxis_rangeslider_visible=False, hovermode="x")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    col_v, col_r = st.columns(2)

    with col_v:
        section("VOLUME")
        vol_colors = [GREEN if c >= o else RED for c, o in zip(grp["close"], grp["open"])]
        fig2 = go.Figure(go.Bar(
            x=grp["date_cours"], y=grp["volume"],
            marker_color=vol_colors,
        ))
        chart(fig2, height=220)
        fig2.update_layout(showlegend=False, yaxis_title="Volume")
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    with col_r:
        section("RSI (14J)")
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=grp["date_cours"], y=grp["rsi_14"].round(1),
            mode="lines", name="RSI",
            line=dict(color=ACCENT, width=2),
            fill="tozeroy", fillcolor=_rgba(ACCENT, 0.09),
        ))
        fig3.add_hline(y=70, line_color=RED,   line_dash="dash", line_width=1)
        fig3.add_hline(y=30, line_color=GREEN, line_dash="dash", line_width=1)
        fig3.add_hrect(y0=70, y1=100, fillcolor=_rgba(RED,   0.06), line_width=0)
        fig3.add_hrect(y0=0,  y1=30,  fillcolor=_rgba(GREEN, 0.06), line_width=0)
        chart(fig3, height=220)
        fig3.update_layout(showlegend=False, yaxis=dict(range=[0, 100], title="RSI"))
        st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    try:
        df_raw = load_data()
    except Exception:
        df_raw = pd.DataFrame()
    df_raw = ensure_data(df_raw)
    engine = get_db()
    try_auto_refresh(df_raw, engine)
    if st.session_state.get("auto_refresh_tried") and not df_raw.empty:
        df_raw = load_data()

    ticker_sel, date_range, page = sidebar(df_raw)

    if not ticker_sel:
        st.info("Sélectionnez au moins un instrument dans la barre latérale.")
        return

    df      = filter_df(df_raw, ticker_sel, date_range)
    if page != "Accueil":
        data_quality_banner(data_quality(df_raw, engine))

    ALL = {
        "Accueil":                   lambda: page_accueil(df_raw, engine),
        "Vue Marché":                lambda: page_marche(df),
        "Risque & Indicateurs":      lambda: page_risque(df),
        "Corrélations":              lambda: page_correlations(df),
        "Bougies":                   lambda: page_bougie(df),
        "Book Produits":             lambda: page_book_produits(engine, df_raw),
        "Alertes Sales":             lambda: page_alertes_sales(engine, df_raw),
        "Dashboard Manager":         lambda: page_dashboard_manager(engine, df_raw),
        "Comparateur":               lambda: page_comparateur(engine, df_raw),
        "Suivi Produits Structurés": lambda: page_suivi_produits(engine, df_raw),
        "Simulateur Autocall":       lambda: page_simulateur(engine, df_raw),
        "Vue Clients":               lambda: page_clients(engine, df_raw),
        "Pitch Client":              lambda: page_pitch_client(engine, df_raw),
        "Meeting Pack":              lambda: page_meeting_pack(engine, df_raw),
        "Screener Sous-jacents":     lambda: page_screener(df_raw, engine),
    }

    fn = ALL.get(page)
    if fn:
        fn()
    else:
        st.error(f"Page inconnue : {page!r}")


if __name__ == "__main__":
    main()
