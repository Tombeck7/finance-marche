# Guide Power BI — Finance de marché

## 1. Prérequis

1. Exécuter le pipeline Python pour alimenter la base :
   ```powershell
   cd python
   python scripts/run_pipeline.py
   ```
2. Installer le connecteur **SQLite ODBC** (ou migrer vers SQL Server pour la production).

## 2. Connexion aux données

### Option A — SQLite (développement local)

1. Ouvrir **Power BI Desktop**
2. **Obtenir des données** → **ODBC** → DSN pointant vers `data/finance_marche.db`
3. Sélectionner la vue `vw_dashboard_marche`

### Option B — SQL Server (recommandé en entreprise)

1. Migrer le schéma `sql/schema/` vers SQL Server
2. Configurer `DATABASE_URL` dans `.env` (voir `config/settings.example.env`)
3. Relancer le pipeline Python
4. Power BI → **SQL Server** → DirectQuery ou Import sur `vw_dashboard_marche`

### Option C — Export CSV (sans ODBC)

Exporter la vue en CSV depuis Python, puis importer dans Power BI :

```powershell
python -c "import pandas as pd; from sqlalchemy import create_engine; e=create_engine('sqlite:///../data/finance_marche.db'); pd.read_sql('SELECT * FROM vw_dashboard_marche', e).to_csv('../powerbi/data/export_dashboard.csv', index=False)"
```

## 3. Modèle recommandé

| Table / Vue            | Rôle                          |
|------------------------|-------------------------------|
| `vw_dashboard_marche`  | Table de faits principale     |
| Calendrier (générée)   | Dimension temps               |

Relations :
- `Calendrier[Date]` → `vw_dashboard_marche[date_cours]` (1:N)

## 4. Mesures DAX

Copier les mesures depuis :
- `powerbi/dax/mesures_rendement.dax`
- `powerbi/dax/mesures_risque.dax`

## 5. Pages de rapport suggérées

1. **Vue marché** — courbes de prix, rendement YTD par secteur
2. **Risque** — volatilité annualisée, drawdown, heatmap corrélation
3. **Signaux** — RSI, SMA50, filtres par type d'instrument (indice / action / ETF)

## 6. Actualisation

Relancer `python/scripts/run_pipeline.py` puis actualiser le rapport Power BI (Planifier via Power BI Service si SQL Server).
