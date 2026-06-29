-- Seed produits structurés — IDs explicites pour éviter les problèmes d'auto-incrément
DELETE FROM fact_position_client;
DELETE FROM dim_produit_structure;
DELETE FROM dim_client;
DELETE FROM sqlite_sequence WHERE name IN ('dim_produit_structure','dim_client','fact_position_client');

INSERT INTO dim_produit_structure (produit_id, nom, isin, type_produit, sous_jacent_1, sous_jacent_2, sous_jacent_3, strike_1, strike_2, strike_3, barriere_ki_pct, barriere_rappel_pct, coupon_annuel_pct, periodicite_obs, date_emission, date_echeance, nominal, note) VALUES
(1, 'Autocall S&P500 8% 2024-2027',   'XS001000001', 'autocall',           '^GSPC',     NULL,        NULL,   4500, NULL, NULL, 0.60, 1.00,  8.0, 'trimestrielle', '2024-03-15', '2027-03-15', 100000, 'Rappel si S&P500 >= 100% du strike'),
(2, 'Autocall CAC40 7% 2024-2028',    'XS001000002', 'autocall',           '^FCHI',     NULL,        NULL,   7500, NULL, NULL, 0.60, 1.00,  7.0, 'trimestrielle', '2024-06-01', '2028-06-01', 100000, 'Rappel si CAC40 >= 100%'),
(3, 'Autocall Step-down AAPL 10%',    'XS001000003', 'autocall',           'AAPL',      NULL,        NULL,    185, NULL, NULL, 0.55, 0.95, 10.0, 'semestrielle',  '2024-01-15', '2027-01-15',  50000, 'Niveau de rappel décroissant'),
(4, 'RC BNP Paribas 9% 1an',          'XS001000004', 'reverse_convertible','BNP.PA',    NULL,        NULL,     55, NULL, NULL, 0.70, 1.00,  9.0, 'annuelle',      '2025-01-10', '2026-01-10', 100000, 'Coupon garanti 9%'),
(5, 'RC LVMH 8% 1an',                 'XS001000005', 'reverse_convertible','MC.PA',     NULL,        NULL,    750, NULL, NULL, 0.70, 1.00,  8.0, 'annuelle',      '2025-03-01', '2026-03-01', 100000, 'Coupon garanti 8%'),
(6, 'Worst-Of CAC/STOXX/S&P 9%',      'XS001000006', 'worst_of_autocall',  '^FCHI', '^STOXX50E', '^GSPC',   7500, 4200, 4500, 0.55, 1.00,  9.0, 'trimestrielle', '2024-09-01', '2027-09-01', 100000, 'Worst-of 3 indices'),
(7, 'Worst-Of AAPL/MSFT 11%',         'XS001000007', 'worst_of_autocall',  'AAPL',     'MSFT',       NULL,    185,  380, NULL, 0.60, 1.00, 11.0, 'trimestrielle', '2024-06-15', '2027-06-15',  50000, 'Worst-of tech US'),
(8, 'Capital Protégé S&P 100% 4ans',  'XS001000008', 'capital_protected',  '^GSPC',     NULL,        NULL,   4500, NULL, NULL, 1.00, 1.20,  3.5, 'annuelle',      '2023-06-01', '2027-06-01', 100000, 'Capital 100% garanti');

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
(1, 6, '2024-09-01', 150000),
(2, 3, '2024-01-15', 100000),
(2, 7, '2024-06-15', 100000),
(2, 1, '2024-03-15', 100000),
(3, 8, '2023-06-01', 200000),
(3, 4, '2025-01-10', 100000),
(4, 6, '2024-09-01', 500000),
(4, 7, '2024-06-15', 300000),
(5, 2, '2024-06-01', 150000),
(5, 5, '2025-03-01', 100000),
(6, 8, '2023-06-01', 100000),
(6, 4, '2025-01-10', 100000),
(7, 3, '2024-01-15',  50000),
(7, 7, '2024-06-15', 100000),
(7, 6, '2024-09-01', 200000);
