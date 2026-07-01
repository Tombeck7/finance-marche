-- Seed produits structurés — IDs explicites
-- Idempotent : ne détruit jamais les données métier déjà saisies/importées.

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
    barriere_ki_pct     REAL NOT NULL,
    barriere_rappel_pct REAL NOT NULL,
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

CREATE TABLE IF NOT EXISTS dim_client (
    client_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    nom         TEXT NOT NULL,
    prenom      TEXT,
    profil      TEXT DEFAULT 'equilibre' CHECK (profil IN ('conservateur','equilibre','dynamique')),
    segment     TEXT DEFAULT 'retail'    CHECK (segment IN ('retail','wealth','institutionnel')),
    actif       INTEGER DEFAULT 1
);

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

-- type_produit : autocall | reverse_convertible | capital_protected | cln
INSERT OR IGNORE INTO dim_produit_structure
  (produit_id, nom, isin, type_produit,
   sous_jacent_1, sous_jacent_2, sous_jacent_3,
   strike_1,  strike_2, strike_3,
   barriere_ki_pct, barriere_rappel_pct, coupon_annuel_pct,
   periodicite_obs, date_emission, date_echeance, nominal,
   reference_entity, recovery_rate_pct, credit_spread_bps, credit_event,
   payoff_summary, sales_argument, main_risk, next_action, note)
VALUES
-- Autocalls
(1, 'Autocall S&P500 8% 2024-2027',  'XS001000001', 'autocall',
   '^GSPC',  NULL, NULL, 4500, NULL, NULL, 0.60, 1.00,  8.0,
   'trimestrielle', '2024-03-15', '2027-03-15', 100000,
   NULL, NULL, NULL, NULL,
   'Coupon potentiel 8%/an avec rappel automatique si le S&P 500 revient au-dessus du strike.',
   'Convient à un client qui accepte le risque actions pour viser un rendement supérieur au monétaire.',
   'Risque de perte en capital si le S&P 500 termine sous la barrière knock-in.',
   'Surveiller les dates trimestrielles de rappel et la distance à la barrière.',
   'Rappel automatique si S&P500 >= 100% du strike initial'),

(2, 'Autocall CAC40 7% 2024-2028',   'XS001000002', 'autocall',
   '^FCHI',  NULL, NULL, 7500, NULL, NULL, 0.60, 1.00,  7.0,
   'trimestrielle', '2024-06-01', '2028-06-01', 100000,
   NULL, NULL, NULL, NULL,
   'Coupon potentiel 7%/an avec rappel automatique si le CAC 40 revient au-dessus du strike.',
   'Idée simple pour jouer une stabilisation du marché français avec coupon conditionnel.',
   'Risque actions France en cas de forte baisse du CAC 40.',
   'Prioriser le suivi des observations et du niveau CAC 40 vs strike.',
   'Rappel si CAC40 >= 100% du strike'),

(3, 'Autocall Step-down AAPL 10%',   'XS001000003', 'autocall',
   'AAPL',   NULL, NULL,  185, NULL, NULL, 0.55, 0.95, 10.0,
   'semestrielle',  '2024-01-15', '2027-01-15',  50000,
   NULL, NULL, NULL, NULL,
   'Coupon potentiel 10%/an avec seuil de rappel step-down à 95% du strike.',
   'Coupon élevé sur une action très suivie, intéressant pour profil dynamique.',
   'Risque spécifique Apple et volatilité action individuelle.',
   'Vérifier concentration client sur la tech US avant proposition.',
   'Niveau de rappel décroissant chaque semestre'),

-- Reverse Convertibles
(4, 'RC BNP Paribas 9% 1an',         'XS001000004', 'reverse_convertible',
   'BNP.PA', NULL, NULL,   55, NULL, NULL, 0.70, 1.00,  9.0,
   'annuelle', '2025-01-10', '2026-01-10', 100000,
   NULL, NULL, NULL, NULL,
   'Coupon 9% avec remboursement espèces si BNP reste au-dessus de la barrière.',
   'Produit court terme pour client acceptant une possible livraison actions BNP.',
   'Risque de livraison actions si la barrière est touchée et le titre finit bas.',
   'A utiliser seulement si le client accepte de détenir BNP Paribas.',
   'Coupon garanti 9% — livraison actions si KI déclenché'),

(5, 'RC LVMH 8% 1an',                'XS001000005', 'reverse_convertible',
   'MC.PA',  NULL, NULL,  750, NULL, NULL, 0.70, 1.00,  8.0,
   'annuelle', '2025-03-01', '2026-03-01', 100000,
   NULL, NULL, NULL, NULL,
   'Coupon 8% avec exposition conditionnelle à LVMH.',
   'Positionnement premium sur une grande capitalisation française avec coupon attractif.',
   'Risque de baisse du luxe et livraison actions si scénario défavorable.',
   'Contrôler la sensibilité client au secteur luxe.',
   'Coupon garanti 8% — livraison actions si KI déclenché'),

-- Capital Protégé
(6, 'Capital Protégé S&P 100% 4ans', 'XS001000006', 'capital_protected',
   '^GSPC',  NULL, NULL, 4500, NULL, NULL, 1.00, 1.20,  3.5,
   'annuelle', '2023-06-01', '2027-06-01', 100000,
   NULL, NULL, NULL, NULL,
   'Capital 100% protégé à échéance avec participation partielle à la hausse du S&P 500.',
   'Solution défensive pour client prudent qui veut rester exposé aux marchés.',
   'Risque d’opportunité : rendement plafonné ou inférieur à une exposition directe.',
   'Mettre en avant la protection du capital pour profils conservateurs.',
   'Capital 100% garanti à l''échéance + participation hausse S&P500'),

-- CLN (Credit-Linked Notes)
(7, 'CLN BNP Paribas 6.5% 2ans',     'XS001000007', 'cln',
   'BNP.PA', NULL, NULL,   55, NULL, NULL, 0.40, 1.00,  6.5,
   'annuelle', '2024-09-01', '2026-09-01', 100000,
   'BNP Paribas', 40.0, 285.0, 'Défaut, faillite, restructuration ou non-paiement',
   'Coupon 6.5%/an tant qu’aucun événement de crédit ne touche BNP Paribas.',
   'Alternative obligataire à coupon élevé pour client acceptant un risque de crédit bancaire.',
   'Perte potentielle en cas d’événement de crédit sur BNP Paribas.',
   'Vérifier que le client comprend le risque crédit et le taux de recouvrement.',
   'Coupon 6.5% — risque de crédit sur BNP Paribas. Perte en cas d''événement de crédit'),

(8, 'CLN TotalEnergies 7% 3ans',      'XS001000008', 'cln',
   'TTE.PA', NULL, NULL,   55, NULL, NULL, 0.40, 1.00,  7.0,
   'annuelle', '2024-06-15', '2027-06-15', 100000,
   'TotalEnergies', 40.0, 320.0, 'Défaut, faillite, restructuration ou non-paiement',
   'Coupon 7%/an lié au risque crédit TotalEnergies.',
   'Coupon attractif sur un grand corporate énergie pour client à profil équilibré/dynamique.',
   'Risque de crédit corporate et exposition sectorielle énergie.',
   'Limiter la taille de position et vérifier les expositions sectorielles existantes.',
   'Coupon 7% — risque de crédit sur TotalEnergies. Taux de recouvrement estimé 40%');

INSERT OR IGNORE INTO dim_client (client_id, nom, prenom, profil, segment) VALUES
(1, 'Dupont',  'Jean',    'equilibre',    'wealth'),
(2, 'Martin',  'Sophie',  'dynamique',    'wealth'),
(3, 'Bernard', 'Pierre',  'conservateur', 'retail'),
(4, 'Leblanc', 'Marie',   'dynamique',    'institutionnel'),
(5, 'Moreau',  'Paul',    'equilibre',    'wealth'),
(6, 'Petit',   'Claire',  'conservateur', 'retail'),
(7, 'Simon',   'Thomas',  'dynamique',    'wealth');

INSERT OR IGNORE INTO fact_position_client (client_id, produit_id, date_souscription, nominal_souscrit) VALUES
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
