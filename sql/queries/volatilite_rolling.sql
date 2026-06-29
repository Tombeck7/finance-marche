-- Volatilité annualisée glissante sur 20 jours ouvrés
SELECT
    i.ticker,
    p.date_cours,
    p.close,
    ind.volatilite_20j,
    ROUND(ind.volatilite_20j * SQRT(252) * 100, 2) AS volatilite_ann_pct
FROM fact_indicateurs ind
JOIN dim_instrument i ON i.instrument_id = ind.instrument_id
JOIN fact_prix p ON p.instrument_id = ind.instrument_id
                AND p.date_cours = ind.date_cours
WHERE ind.volatilite_20j IS NOT NULL
ORDER BY i.ticker, p.date_cours DESC;
