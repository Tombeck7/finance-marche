"""Téléchargement des cours de marché via Yahoo Finance."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from ..config import DEFAULT_TICKERS


def fetch_market_data(
    tickers: list[str] | None = None,
    period: str = "2y",
) -> pd.DataFrame:
    """Télécharge les cours OHLCV via Yahoo Finance.

    Compatible yfinance >= 0.2.x (MultiIndex columns).
    Le CSV de sauvegarde est optionnel et silencieusement ignoré si
    le filesystem est en lecture seule (Streamlit Cloud).
    """
    tickers = tickers or DEFAULT_TICKERS

    # Dates explicites pour garantir les données les plus récentes
    end_date   = date.today()
    start_date = end_date - timedelta(days=365 * 2 + 30)  # ~2 ans + marge

    raw = yf.download(
        tickers,
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
        auto_adjust=True,
        progress=False,
        threads=True,
    )

    if raw.empty:
        return pd.DataFrame()

    frames: list[pd.DataFrame] = []

    for ticker in tickers:
        try:
            # yfinance >= 0.2.x : colonnes MultiIndex (Price, Ticker)
            if isinstance(raw.columns, pd.MultiIndex):
                if ticker in raw.columns.get_level_values(1):
                    df = raw.xs(ticker, axis=1, level=1).copy()
                elif ticker in raw.columns.get_level_values(0):
                    df = raw[ticker].copy()
                else:
                    continue
            else:
                # Un seul ticker
                df = raw.copy()

            df = df.reset_index()
            # Renomme les colonnes (minuscule, sans espace)
            df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]

            # Colonne date peut s'appeler 'date', 'datetime', 'price' selon la version
            for date_col in ("date", "datetime", "price"):
                if date_col in df.columns:
                    df = df.rename(columns={date_col: "date_cours"})
                    break

            if "date_cours" not in df.columns:
                continue

            df["ticker"]     = ticker
            df["date_cours"] = pd.to_datetime(df["date_cours"]).dt.strftime("%Y-%m-%d")
            df = df.dropna(subset=["close"])

            if not df.empty:
                frames.append(df)

        except Exception:
            continue

    if not frames:
        return pd.DataFrame()

    result = pd.concat(frames, ignore_index=True)

    # Sauvegarde CSV optionnelle (ignorée sur Streamlit Cloud)
    try:
        from ..config import DATA_RAW
        from datetime import datetime
        DATA_RAW.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        result.to_csv(DATA_RAW / f"cours_marche_{stamp}.csv", index=False)
    except Exception:
        pass

    return result
