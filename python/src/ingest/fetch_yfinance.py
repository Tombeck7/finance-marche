"""Téléchargement des cours de marché via Yahoo Finance."""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from ..config import DATA_RAW, DEFAULT_TICKERS


def fetch_market_data(
    tickers: list[str] | None = None,
    period: str = "2y",
) -> pd.DataFrame:
    tickers = tickers or DEFAULT_TICKERS
    raw = yf.download(
        tickers,
        period=period,
        group_by="ticker",
        auto_adjust=True,
        progress=False,
    )

    frames: list[pd.DataFrame] = []
    for ticker in tickers:
        if len(tickers) == 1:
            df = raw.copy()
        else:
            df = raw[ticker].copy()

        df = df.reset_index()
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        df["ticker"] = ticker
        df = df.rename(columns={"date": "date_cours"})
        df["date_cours"] = pd.to_datetime(df["date_cours"]).dt.strftime("%Y-%m-%d")
        frames.append(df.dropna(subset=["close"]))

    result = pd.concat(frames, ignore_index=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    out = DATA_RAW / f"cours_marche_{stamp}.csv"
    result.to_csv(out, index=False)
    return result


def fetch_latest(days: int = 30, tickers: list[str] | None = None) -> pd.DataFrame:
    end = datetime.now()
    start = end - timedelta(days=days)
    tickers = tickers or DEFAULT_TICKERS
    raw = yf.download(
        tickers,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        group_by="ticker",
        auto_adjust=True,
        progress=False,
    )
    return raw
