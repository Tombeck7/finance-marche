"""Générateur de données synthétiques (fallback quand Yahoo Finance est inaccessible)."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from ..config import DEFAULT_TICKERS

_PARAMS: dict[str, dict] = {
    "^GSPC":    {"prix_init": 4500, "mu": 0.0003, "sigma": 0.010, "volume_base": 3_000_000_000},
    "^FCHI":    {"prix_init": 7500, "mu": 0.0002, "sigma": 0.012, "volume_base": 1_500_000_000},
    "^STOXX50E":{"prix_init": 4200, "mu": 0.0002, "sigma": 0.011, "volume_base": 2_000_000_000},
    "AAPL":     {"prix_init": 185,  "mu": 0.0004, "sigma": 0.015, "volume_base": 60_000_000},
    "MSFT":     {"prix_init": 380,  "mu": 0.0004, "sigma": 0.013, "volume_base": 25_000_000},
    "BNP.PA":   {"prix_init": 55,   "mu": 0.0002, "sigma": 0.018, "volume_base": 5_000_000},
    "MC.PA":    {"prix_init": 750,  "mu": 0.0003, "sigma": 0.016, "volume_base": 500_000},
    "SPY":      {"prix_init": 450,  "mu": 0.0003, "sigma": 0.010, "volume_base": 80_000_000},
    "CAC.PA":   {"prix_init": 36,   "mu": 0.0002, "sigma": 0.012, "volume_base": 800_000},
    "EURUSD=X": {"prix_init": 1.08, "mu": 0.0000, "sigma": 0.004, "volume_base": 0},
}


def _generate_ohlcv(
    ticker: str,
    days: int,
    end: date | None = None,
    seed: int | None = None,
) -> pd.DataFrame:
    params = _PARAMS.get(ticker, {"prix_init": 100, "mu": 0.0002, "sigma": 0.012, "volume_base": 1_000_000})
    rng = np.random.default_rng(seed or abs(hash(ticker)) % (2**31))

    end = end or date.today()
    all_days: list[date] = []
    d = end - timedelta(days=days * 2)
    while len(all_days) < days and d <= end:
        if d.weekday() < 5:
            all_days.append(d)
        d += timedelta(days=1)
    all_days = all_days[-days:]

    n = len(all_days)
    log_returns = rng.normal(params["mu"], params["sigma"], n)
    close = params["prix_init"] * np.exp(np.cumsum(log_returns))

    daily_range = close * params["sigma"] * rng.uniform(0.5, 1.5, n)
    high = close + daily_range * rng.uniform(0.3, 0.7, n)
    low = close - daily_range * rng.uniform(0.3, 0.7, n)
    open_ = low + (high - low) * rng.uniform(0.2, 0.8, n)

    vol_base = params["volume_base"]
    volume = vol_base * rng.lognormal(0, 0.3, n) if vol_base > 0 else np.zeros(n)

    return pd.DataFrame({
        "ticker":     [ticker] * n,
        "date_cours": [str(d) for d in all_days],
        "open":       open_.round(4),
        "high":       high.round(4),
        "low":        low.round(4),
        "close":      close.round(4),
        "volume":     volume.round(0),
    })


def generate_demo_data(
    tickers: list[str] | None = None,
    days: int = 500,
) -> pd.DataFrame:
    """Génère ~2 ans de données OHLCV synthétiques pour tous les instruments."""
    tickers = tickers or DEFAULT_TICKERS
    frames = [_generate_ohlcv(t, days) for t in tickers]
    return pd.concat(frames, ignore_index=True)
