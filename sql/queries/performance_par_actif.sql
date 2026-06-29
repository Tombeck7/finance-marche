-- Rendement cumulé par instrument sur les 12 derniers mois
SELECT
    i.ticker,
    i.nom,
    i.type_instrument,
    MIN(p.date_cours)   AS date_debut,
    MAX(p.date_cours)   AS date_fin,
    COUNT(*)            AS nb_jours,
    ROUND(
        (MAX(p.close) / MIN(p.close) - 1) * 100, 2
    )                   AS rendement_pct_periode
FROM fact_prix p
JOIN dim_instrument i ON i.instrument_id = p.instrument_id
WHERE p.date_cours >= date('now', '-12 months')
  AND i.actif = 1
GROUP BY i.ticker, i.nom, i.type_instrument
ORDER BY rendement_pct_periode DESC;
