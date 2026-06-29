# Finance de marché — Python + SQL + Power BI

Projet d'analyse des marchés financiers combinant trois briques :

| Couche      | Rôle                                              |
|-------------|---------------------------------------------------|
| **Python**  | Ingestion Yahoo Finance, calcul d'indicateurs     |
| **SQL**     | Stockage structuré, vues analytiques              |
| **Power BI**| Tableaux de bord interactifs (rendement, risque)  |

## Structure

```
finance-marche/
├── python/          # Pipeline de données
│   ├── src/         # Modules (ingestion, analytics, SQL)
│   └── scripts/     # run_pipeline.py
├── sql/
│   ├── schema/      # Tables et vues
│   ├── seed/        # Instruments de référence
│   └── queries/     # Requêtes analytiques
├── powerbi/
│   ├── dax/         # Mesures DAX prêtes à l'emploi
│   └── README.md    # Guide de connexion Power BI
└── data/            # Base SQLite + exports CSV
```

## Démarrage rapide

```powershell
# 1. Environnement Python
cd C:\Users\tbeckermann\Projects\finance-marche
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Configuration (optionnel)
copy config\settings.example.env .env

# 3. Lancer le pipeline complet
cd python
python scripts\run_pipeline.py
```

Le pipeline :
1. Crée la base SQLite (`data/finance_marche.db`)
2. Télécharge 2 ans de cours (S&P 500, CAC 40, actions, ETF…)
3. Calcule rendements, volatilité, SMA, RSI
4. Alimente les tables SQL et la vue `vw_dashboard_marche`

## Instruments suivis par défaut

- Indices : S&P 500, CAC 40, Euro Stoxx 50
- Actions : Apple, Microsoft, BNP Paribas, LVMH
- ETF : SPY, Amundi CAC 40
- Forex : EUR/USD

Modifiable dans `python/src/config.py` (`DEFAULT_TICKERS`).

## Requêtes SQL utiles

```powershell
sqlite3 data/finance_marche.db < sql/queries/performance_par_actif.sql
sqlite3 data/finance_marche.db < sql/queries/correlation_matrix.sql
```

## Power BI

Voir [powerbi/README.md](powerbi/README.md) pour connecter le rapport à la base et importer les mesures DAX.

## Prochaines étapes possibles

- Migration vers SQL Server pour DirectQuery en production
- Ajout de données macro (taux, inflation) et de dérivés
- Backtesting de stratégies dans Python
- Publication sur Power BI Service avec actualisation planifiée
