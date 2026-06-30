-- ============================================================
-- Produits structurés — schéma
-- ============================================================

-- Catalogue des produits
CREATE TABLE IF NOT EXISTS dim_produit_structure (
    produit_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nom                 TEXT NOT NULL,
    isin                TEXT,
    type_produit        TEXT NOT NULL CHECK (type_produit IN (
                            'autocall', 'reverse_convertible',
                            'capital_protected', 'cln'
                        )),
    sous_jacent_1       TEXT NOT NULL,
    sous_jacent_2       TEXT,
    sous_jacent_3       TEXT,
    strike_1            REAL NOT NULL,
    strike_2            REAL,
    strike_3            REAL,
    barriere_ki_pct     REAL NOT NULL,   -- knock-in en % du strike (ex: 0.60)
    barriere_rappel_pct REAL NOT NULL,   -- niveau de rappel autocall (ex: 1.00)
    coupon_annuel_pct   REAL NOT NULL,
    periodicite_obs     TEXT DEFAULT 'trimestrielle',
    date_emission       TEXT NOT NULL,
    date_echeance       TEXT NOT NULL,
    nominal             REAL DEFAULT 100000,
    devise              TEXT DEFAULT 'EUR',
    actif               INTEGER DEFAULT 1,
    reference_entity    TEXT,
    recovery_rate_pct   REAL,
    credit_spread_bps   REAL,
    credit_event        TEXT,
    payoff_summary      TEXT,
    sales_argument      TEXT,
    main_risk           TEXT,
    next_action         TEXT,
    note                TEXT
);

-- Dates d'observation autocall
CREATE TABLE IF NOT EXISTS fact_observation_autocall (
    obs_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    produit_id          INTEGER NOT NULL,
    date_observation    TEXT NOT NULL,
    niveau_rappel_pct   REAL NOT NULL,
    cours_sj1           REAL,
    cours_sj2           REAL,
    cours_sj3           REAL,
    perf_sj1_pct        REAL,
    perf_sj2_pct        REAL,
    perf_sj3_pct        REAL,
    perf_worst_of_pct   REAL,
    rappele             INTEGER DEFAULT 0,
    coupon_verse        REAL DEFAULT 0,
    FOREIGN KEY (produit_id) REFERENCES dim_produit_structure(produit_id),
    UNIQUE (produit_id, date_observation)
);

CREATE INDEX IF NOT EXISTS idx_obs_produit ON fact_observation_autocall (produit_id);
CREATE INDEX IF NOT EXISTS idx_obs_date    ON fact_observation_autocall (date_observation);

-- Clients
CREATE TABLE IF NOT EXISTS dim_client (
    client_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    nom         TEXT NOT NULL,
    prenom      TEXT,
    profil      TEXT DEFAULT 'equilibre' CHECK (profil IN (
                    'conservateur', 'equilibre', 'dynamique'
                )),
    segment     TEXT DEFAULT 'retail' CHECK (segment IN (
                    'retail', 'wealth', 'institutionnel'
                )),
    actif       INTEGER DEFAULT 1
);

-- Positions client sur les produits
CREATE TABLE IF NOT EXISTS fact_position_client (
    position_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id           INTEGER NOT NULL,
    produit_id          INTEGER NOT NULL,
    date_souscription   TEXT NOT NULL,
    nominal_souscrit    REAL NOT NULL,
    prix_souscription   REAL DEFAULT 100,
    FOREIGN KEY (client_id)  REFERENCES dim_client(client_id),
    FOREIGN KEY (produit_id) REFERENCES dim_produit_structure(produit_id),
    UNIQUE (client_id, produit_id)
);
