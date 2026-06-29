-- Schéma principal — compatible SQLite et SQL Server
-- Exécuter dans l'ordre numérique

-- ============================================================
-- 01 — Instruments financiers (actions, indices, ETF)
-- ============================================================
CREATE TABLE IF NOT EXISTS dim_instrument (
    instrument_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker          TEXT NOT NULL UNIQUE,
    nom             TEXT NOT NULL,
    type_instrument TEXT NOT NULL CHECK (type_instrument IN ('action', 'indice', 'etf', 'devise')),
    secteur         TEXT,
    devise          TEXT DEFAULT 'USD',
    actif           INTEGER DEFAULT 1,
    date_creation   TEXT DEFAULT (datetime('now'))
);

-- ============================================================
-- 02 — Prix OHLCV quotidiens
-- ============================================================
CREATE TABLE IF NOT EXISTS fact_prix (
    prix_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument_id   INTEGER NOT NULL,
    date_cours      TEXT NOT NULL,
    open            REAL,
    high            REAL,
    low             REAL,
    close           REAL NOT NULL,
    volume          REAL,
    rendement_jour  REAL,
    FOREIGN KEY (instrument_id) REFERENCES dim_instrument(instrument_id),
    UNIQUE (instrument_id, date_cours)
);

CREATE INDEX IF NOT EXISTS idx_fact_prix_date ON fact_prix (date_cours);
CREATE INDEX IF NOT EXISTS idx_fact_prix_instrument ON fact_prix (instrument_id);

-- ============================================================
-- 03 — Indicateurs calculés (volatilité, moyennes mobiles)
-- ============================================================
CREATE TABLE IF NOT EXISTS fact_indicateurs (
    indicateur_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument_id   INTEGER NOT NULL,
    date_cours      TEXT NOT NULL,
    volatilite_20j  REAL,
    sma_20          REAL,
    sma_50          REAL,
    rsi_14          REAL,
    FOREIGN KEY (instrument_id) REFERENCES dim_instrument(instrument_id),
    UNIQUE (instrument_id, date_cours)
);
