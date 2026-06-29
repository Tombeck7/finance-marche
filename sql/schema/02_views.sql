-- Vue consolidée pour Power BI (Import ou DirectQuery)
CREATE VIEW IF NOT EXISTS vw_dashboard_marche AS
SELECT
    i.instrument_id,
    i.ticker,
    i.nom,
    i.type_instrument,
    i.secteur,
    i.devise,
    p.date_cours,
    p.open,
    p.high,
    p.low,
    p.close,
    p.volume,
    p.rendement_jour,
    ind.volatilite_20j,
    ind.sma_20,
    ind.sma_50,
    ind.rsi_14,
    CASE
        WHEN p.close > ind.sma_50 THEN 'Au-dessus SMA50'
        ELSE 'Sous SMA50'
    END AS signal_tendance
FROM fact_prix p
JOIN dim_instrument i ON i.instrument_id = p.instrument_id
LEFT JOIN fact_indicateurs ind
    ON ind.instrument_id = p.instrument_id
   AND ind.date_cours = p.date_cours
WHERE i.actif = 1;
