"""Calculs de rendement et volatilité."""

from __future__ import annotations

import numpy as np
import pandas as pd


def daily_returns(prices: pd.Series) -> pd.Series:
    return prices.pct_change()


def rolling_volatility(returns: pd.Series, window: int = 20) -> pd.Series:
    return returns.rolling(window).std()


def annualized_volatility(returns: pd.Series, window: int = 20) -> pd.Series:
    return rolling_volatility(returns, window) * np.sqrt(252)


def sma(prices: pd.Series, window: int) -> pd.Series:
    return prices.rolling(window).mean()


def rsi(prices: pd.Series, window: int = 14) -> pd.Series:
    delta = prices.diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = (-delta.clip(upper=0)).rolling(window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def enrich_with_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute rendement, volatilité, SMA et RSI à un DataFrame par ticker."""
    parts: list[pd.DataFrame] = []
    for ticker, group in df.groupby("ticker"):
        g = group.sort_values("date_cours").copy()
        g["rendement_jour"] = daily_returns(g["close"])
        g["volatilite_20j"] = rolling_volatility(g["rendement_jour"], 20)
        g["sma_20"] = sma(g["close"], 20)
        g["sma_50"] = sma(g["close"], 50)
        g["rsi_14"] = rsi(g["close"], 14)
        parts.append(g)
    return pd.concat(parts, ignore_index=True)
