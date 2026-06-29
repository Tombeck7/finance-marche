-- Matrice de corrélation des rendements quotidiens (derniers 6 mois)
-- Résultat : paires d'instruments avec coefficient de corrélation
WITH rendements AS (
    SELECT
        i.ticker,
        p.date_cours,
        p.rendement_jour
    FROM fact_prix p
    JOIN dim_instrument i ON i.instrument_id = p.instrument_id
    WHERE p.date_cours >= date('now', '-6 months')
      AND p.rendement_jour IS NOT NULL
      AND i.type_instrument IN ('action', 'indice', 'etf')
),
paires AS (
    SELECT
        a.ticker AS ticker_a,
        b.ticker AS ticker_b,
        a.rendement_jour AS rend_a,
        b.rendement_jour AS rend_b
    FROM rendements a
    JOIN rendements b ON a.date_cours = b.date_cours
                     AND a.ticker < b.ticker
)
SELECT
    ticker_a,
    ticker_b,
    ROUND(
        (AVG(rend_a * rend_b) - AVG(rend_a) * AVG(rend_b))
        / (SQRT(AVG(rend_a * rend_a) - AVG(rend_a) * AVG(rend_a))
         * SQRT(AVG(rend_b * rend_b) - AVG(rend_b) * AVG(rend_b))),
        4
    ) AS correlation
FROM paires
GROUP BY ticker_a, ticker_b
ORDER BY correlation DESC;
