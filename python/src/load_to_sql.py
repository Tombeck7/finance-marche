"""Chargement des cours et indicateurs en base SQL."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.analytics.indicators import enrich_with_indicators


def _ticker_map(engine: Engine) -> dict[str, int]:
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT ticker, instrument_id FROM dim_instrument")).fetchall()
    return {r[0]: r[1] for r in rows}


def load_prices(engine: Engine, df: pd.DataFrame) -> int:
    mapping = _ticker_map(engine)
    df = enrich_with_indicators(df)
    inserted = 0

    with engine.begin() as conn:
        for _, row in df.iterrows():
            iid = mapping.get(row["ticker"])
            if iid is None:
                continue

            conn.execute(
                text("""
                    INSERT INTO fact_prix
                        (instrument_id, date_cours, open, high, low, close, volume, rendement_jour)
                    VALUES
                        (:iid, :date, :open, :high, :low, :close, :volume, :rend)
                    ON CONFLICT(instrument_id, date_cours) DO UPDATE SET
                        open = excluded.open,
                        high = excluded.high,
                        low = excluded.low,
                        close = excluded.close,
                        volume = excluded.volume,
                        rendement_jour = excluded.rendement_jour
                """),
                {
                    "iid": iid,
                    "date": row["date_cours"],
                    "open": row.get("open"),
                    "high": row.get("high"),
                    "low": row.get("low"),
                    "close": row["close"],
                    "volume": row.get("volume"),
                    "rend": row.get("rendement_jour"),
                },
            )

            conn.execute(
                text("""
                    INSERT INTO fact_indicateurs
                        (instrument_id, date_cours, volatilite_20j, sma_20, sma_50, rsi_14)
                    VALUES
                        (:iid, :date, :vol, :sma20, :sma50, :rsi)
                    ON CONFLICT(instrument_id, date_cours) DO UPDATE SET
                        volatilite_20j = excluded.volatilite_20j,
                        sma_20 = excluded.sma_20,
                        sma_50 = excluded.sma_50,
                        rsi_14 = excluded.rsi_14
                """),
                {
                    "iid": iid,
                    "date": row["date_cours"],
                    "vol": row.get("volatilite_20j"),
                    "sma20": row.get("sma_20"),
                    "sma50": row.get("sma_50"),
                    "rsi": row.get("rsi_14"),
                },
            )
            inserted += 1

    return inserted
