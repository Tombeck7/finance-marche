-- Jeu de données initial — marchés actions / indices / ETF
INSERT OR IGNORE INTO dim_instrument (ticker, nom, type_instrument, secteur, devise) VALUES
    ('^GSPC',  'S&P 500',              'indice',  'Large Cap US',  'USD'),
    ('^FCHI',  'CAC 40',               'indice',  'Large Cap FR',  'EUR'),
    ('^STOXX50E', 'Euro Stoxx 50',     'indice',  'Large Cap EU',  'EUR'),
    ('AAPL',   'Apple Inc.',           'action',  'Technologie',   'USD'),
    ('MSFT',   'Microsoft Corp.',      'action',  'Technologie',   'USD'),
    ('BNP.PA', 'BNP Paribas',          'action',  'Banque',        'EUR'),
    ('MC.PA',  'LVMH',                 'action',  'Luxe',          'EUR'),
    ('TTE.PA', 'TotalEnergies',        'action',  'Énergie',       'EUR'),
    ('SPY',    'SPDR S&P 500 ETF',     'etf',     'Large Cap US',  'USD'),
    ('CAC.PA', 'Amundi CAC 40 ETF',    'etf',     'Large Cap FR',  'EUR'),
    ('EURUSD=X', 'EUR/USD',            'devise',  'Forex',         'USD');
