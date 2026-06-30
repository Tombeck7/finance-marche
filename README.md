# Entretien Tom Generali — Finance de marché

Application Streamlit de démonstration pour un poste d'assistant sales en produits structurés.
Le projet combine Python, SQL et une interface web pour suivre les marchés, monitorer des produits structurés, préparer un pitch client et exporter des éléments commerciaux.

| Couche      | Rôle                                              |
|-------------|---------------------------------------------------|
| **Python**  | Ingestion Yahoo Finance, fallback démo, indicateurs, simulation Monte-Carlo |
| **SQL**     | Stockage structuré des prix, indicateurs, produits, clients et positions |
| **Streamlit** | Interface sales : marchés, produits structurés, pitch client et exports |

## Structure

```
finance-marche/
├── app.py           # Application Streamlit
├── python/          # Pipeline de données
│   ├── src/         # Modules (ingestion, analytics, SQL)
│   └── scripts/     # run_pipeline.py
├── sql/
│   ├── schema/      # Tables et vues
│   ├── seed/        # Instruments de référence
│   └── queries/     # Requêtes analytiques
├── tests/           # Tests simples des calculs critiques
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

# 3. Lancer l'application
streamlit run app.py
```

L'application :
1. Crée la base SQLite (`data/finance_marche.db`)
2. Essaie de télécharger 2 ans de cours via Yahoo Finance
3. Bascule automatiquement en données démo si Yahoo Finance est indisponible
4. Calcule rendements, volatilité, SMA, RSI
5. Alimente les tables SQL et la vue `vw_dashboard_marche`
6. Affiche les pages marchés, produits structurés, clients, pitch et exports

## Instruments suivis par défaut

- Indices : S&P 500, CAC 40, Euro Stoxx 50
- Actions : Apple, Microsoft, BNP Paribas, LVMH
- ETF : SPY, Amundi CAC 40
- Forex : EUR/USD

Modifiable dans `python/src/config.py` (`DEFAULT_TICKERS`).

## Fonctionnalités métier

- **Accueil** : objectif du projet, architecture Python/SQL/Streamlit, qualité des données.
- **Vue Marché** : performances, rendements, derniers cours.
- **Risque & Indicateurs** : volatilité, RSI, SMA50.
- **Corrélations** : matrice de corrélation et corrélation glissante.
- **Suivi Produits Structurés** : Autocalls, Reverse Convertibles, Capital Protégé, CLN.
- **Vue Clients** : encours, expositions, alertes et fiche client exportable.
- **Pitch Client** : recommandations commerciales selon profil, risque et adéquation.
- **Screener** : idées produits selon volatilité, RSI et tendance.

## Produits structurés couverts

- Autocall
- Reverse Convertible
- Capital Protégé
- CLN (Credit-Linked Note)

## Tests

```powershell
python tests\test_core.py
```

## Déploiement Streamlit Cloud

Le projet est compatible Streamlit Community Cloud :

- `app.py` est le point d'entrée
- `requirements.txt` contient les dépendances Python
- la base SQLite utilise `/tmp` automatiquement si le filesystem cloud est en lecture seule
- Yahoo Finance est tenté en priorité, puis fallback démo
