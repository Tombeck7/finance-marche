-- Seed produits structurés — IDs explicites
-- Recrée la table pour mettre à jour la contrainte CHECK (SQLite ne supporte pas ALTER CONSTRAINT)
DROP TABLE IF EXISTS fact_position_client;
DROP TABLE IF EXISTS fact_observation_autocall;
DROP TABLE IF EXISTS dim_produit_structure;
DROP TABLE IF EXISTS dim_client;

CREATE TABLE dim_produit_structure (
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
    barriere_ki_pct     REAL NOT NULL,
    barriere_rappel_pct REAL NOT NULL,
    coupon_annuel_pct   REAL NOT NULL,
    periodicite_obs     TEXT DEFAULT 'trimestrielle',
    date_emission       TEXT NOT NULL,
    date_echeance       TEXT NOT NULL,
    nominal             REAL DEFAULT 100000,
    devise              TEXT DEFAULT 'EUR',
    actif               INTEGER DEFAULT 1,
    note                TEXT
);

CREATE TABLE dim_client (
    client_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    nom         TEXT NOT NULL,
    prenom      TEXT,
    profil      TEXT DEFAULT 'equilibre' CHECK (profil IN ('conservateur','equilibre','dynamique')),
    segment     TEXT DEFAULT 'retail'    CHECK (segment IN ('retail','wealth','institutionnel')),
    actif       INTEGER DEFAULT 1
);

CREATE TABLE fact_position_client (
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

-- type_produit : autocall | reverse_convertible | capital_protected | cln
INSERT INTO dim_produit_structure
  (produit_id, nom, isin, type_produit,
   sous_jacent_1, sous_jacent_2, sous_jacent_3,
   strike_1,  strike_2, strike_3,
   barriere_ki_pct, barriere_rappel_pct, coupon_annuel_pct,
   periodicite_obs, date_emission, date_echeance, nominal, note)
VALUES
-- Autocalls
(1, 'Autocall S&P500 8% 2024-2027',  'XS001000001', 'autocall',
   '^GSPC',  NULL, NULL, 4500, NULL, NULL, 0.60, 1.00,  8.0,
   'trimestrielle', '2024-03-15', '2027-03-15', 100000,
   'Rappel automatique si S&P500 >= 100% du strike initial'),

(2, 'Autocall CAC40 7% 2024-2028',   'XS001000002', 'autocall',
   '^FCHI',  NULL, NULL, 7500, NULL, NULL, 0.60, 1.00,  7.0,
   'trimestrielle', '2024-06-01', '2028-06-01', 100000,
   'Rappel si CAC40 >= 100% du strike'),

(3, 'Autocall Step-down AAPL 10%',   'XS001000003', 'autocall',
   'AAPL',   NULL, NULL,  185, NULL, NULL, 0.55, 0.95, 10.0,
   'semestrielle',  '2024-01-15', '2027-01-15',  50000,
   'Niveau de rappel décroissant chaque semestre'),

-- Reverse Convertibles
(4, 'RC BNP Paribas 9% 1an',         'XS001000004', 'reverse_convertible',
   'BNP.PA', NULL, NULL,   55, NULL, NULL, 0.70, 1.00,  9.0,
   'annuelle', '2025-01-10', '2026-01-10', 100000,
   'Coupon garanti 9% — livraison actions si KI déclenché'),

(5, 'RC LVMH 8% 1an',                'XS001000005', 'reverse_convertible',
   'MC.PA',  NULL, NULL,  750, NULL, NULL, 0.70, 1.00,  8.0,
   'annuelle', '2025-03-01', '2026-03-01', 100000,
   'Coupon garanti 8% — livraison actions si KI déclenché'),

-- Capital Protégé
(6, 'Capital Protégé S&P 100% 4ans', 'XS001000006', 'capital_protected',
   '^GSPC',  NULL, NULL, 4500, NULL, NULL, 1.00, 1.20,  3.5,
   'annuelle', '2023-06-01', '2027-06-01', 100000,
   'Capital 100% garanti à l''échéance + participation hausse S&P500'),

-- CLN (Credit-Linked Notes)
(7, 'CLN BNP Paribas 6.5% 2ans',     'XS001000007', 'cln',
   'BNP.PA', NULL, NULL,   55, NULL, NULL, 0.40, 1.00,  6.5,
   'annuelle', '2024-09-01', '2026-09-01', 100000,
   'Coupon 6.5% — risque de crédit sur BNP Paribas. Perte en cas d''événement de crédit'),

(8, 'CLN TotalEnergies 7% 3ans',      'XS001000008', 'cln',
   'TTE.PA', NULL, NULL,   55, NULL, NULL, 0.40, 1.00,  7.0,
   'annuelle', '2024-06-15', '2027-06-15', 100000,
   'Coupon 7% — risque de crédit sur TotalEnergies. Taux de recouvrement estimé 40%');

INSERT INTO dim_client (client_id, nom, prenom, profil, segment) VALUES
(1, 'Dupont',  'Jean',    'equilibre',    'wealth'),
(2, 'Martin',  'Sophie',  'dynamique',    'wealth'),
(3, 'Bernard', 'Pierre',  'conservateur', 'retail'),
(4, 'Leblanc', 'Marie',   'dynamique',    'institutionnel'),
(5, 'Moreau',  'Paul',    'equilibre',    'wealth'),
(6, 'Petit',   'Claire',  'conservateur', 'retail'),
(7, 'Simon',   'Thomas',  'dynamique',    'wealth');

INSERT INTO fact_position_client (client_id, produit_id, date_souscription, nominal_souscrit) VALUES
(1, 1, '2024-03-15', 200000),
(1, 7, '2024-09-01', 150000),
(2, 3, '2024-01-15', 100000),
(2, 8, '2024-06-15', 100000),
(2, 1, '2024-03-15', 100000),
(3, 6, '2023-06-01', 200000),
(3, 4, '2025-01-10', 100000),
(4, 7, '2024-09-01', 500000),
(4, 8, '2024-06-15', 300000),
(5, 2, '2024-06-01', 150000),
(5, 5, '2025-03-01', 100000),
(6, 6, '2023-06-01', 100000),
(6, 4, '2025-01-10', 100000),
(7, 3, '2024-01-15',  50000),
(7, 8, '2024-06-15', 100000),
(7, 7, '2024-09-01', 200000);
