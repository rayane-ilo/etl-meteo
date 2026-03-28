# ETL Météo Historique

Pipeline ETL qui extrait des données météo historiques depuis l'API Open-Meteo,
les transforme en modèle dimensionnel Kimball et les charge dans PostgreSQL.

---

## Stack technique

- Python 3.12
- Pandas — transformation et modélisation dimensionnelle
- SQLAlchemy — connexion et chargement PostgreSQL
- PostgreSQL — entrepôt de données analytique
- pytest — 36 tests unitaires, couverture > 90%
- python-dotenv — gestion des variables d'environnement
- API Open-Meteo — données météo historiques gratuites, sans clé

---

## Architecture
```
API Open-Meteo (archive historique)
        |
        v
   extract.py       # Appel API par ville avec pagination et retry
        |
        v
  transform.py      # Modele dimensionnel Kimball
        |            # dim_ville, dim_date, fait_meteo
        v
    load.py         # Upsert PostgreSQL sur 3 tables
        |
        v
  pipeline.py       # Orchestrateur — assemble les 3 etapes

PostgreSQL
  dim_ville         # Referentiel des villes avec coordonnees
  dim_date          # Calendrier avec saisons, trimestres, weekends
  fait_meteo        # Mesures meteo par ville et par jour
  pipeline_runs     # Historique des executions
```

---

## Modele dimensionnel
```
DIM_VILLE              DIM_DATE
─────────              ────────
ville_sk  ◄──┐    ┌──► date_sk
ville_id      │    │    date_id
nom           │    │    annee
region        │    │    mois
pays          │    │    trimestre
latitude      │    │    saison
longitude     │    │    est_weekend

              FAIT_METEO
              ──────────────────
              meteo_sk     (PK)
              ville_id     (FK)
              date_id      (FK)
              temp_max_c
              temp_min_c
              temp_moy_c
              precipitation_mm
              vent_max_kmh
              description_meteo
```

---

## Structure du projet
```
etl-meteo/
├── src/
│   ├── extract.py      # Extraction API Open-Meteo
│   ├── transform.py    # Modele dimensionnel Kimball
│   ├── load.py         # Chargement PostgreSQL
│   └── pipeline.py     # Orchestrateur ETL
├── tests/
│   ├── conftest.py     # Fixtures partagees
│   ├── test_extract.py # Tests extraction
│   ├── test_transform.py # Tests transformation
│   └── test_load.py    # Tests chargement
├── logs/               # Logs d'execution (gitignore)
├── data/               # Donnees brutes (gitignore)
├── .env.example        # Template variables d'environnement
├── requirements.txt
└── README.md
```

---

## Installation
```bash
# Cloner le repo
git clone https://github.com/rayane-ilo/etl-meteo.git
cd etl-meteo

# Creer et activer l'environnement virtuel
python -m venv .venv
source .venv/bin/activate

# Installer les dependances
pip install -r requirements.txt

# Configurer les variables d'environnement
cp .env.example .env
# Editer .env avec vos identifiants PostgreSQL
```

### Configuration PostgreSQL
```sql
CREATE DATABASE meteo_dw;
GRANT ALL ON SCHEMA public TO votre_user;
GRANT CREATE ON SCHEMA public TO votre_user;
```

---

## Utilisation

### Lancer le pipeline
```bash
python -m src.pipeline
```

### Exemple de sortie
```
2024-03-15 10:00:00 | INFO | pipeline | === PIPELINE DEMARRE — 2024-01-01 au 2024-03-31 ===
2024-03-15 10:00:00 | INFO | pipeline | Villes : ['Paris', 'Lyon', 'Marseille', 'Bordeaux']
2024-03-15 10:00:01 | INFO | pipeline | Etape 1/4 : Extraction API
2024-03-15 10:00:04 | INFO | pipeline | Etape 2/4 : Transformation
2024-03-15 10:00:04 | INFO | pipeline | Etape 3/4 : Chargement PostgreSQL
2024-03-15 10:00:04 | INFO | pipeline | Etape 4/4 : Rapport
2024-03-15 10:00:04 | INFO | pipeline | === PIPELINE TERMINE en 4.1s — 364 inseres ===
```

### Lancer les tests
```bash
python -m pytest tests/ -v --cov=src --cov-report=term-missing
```

---

## Schema de la base de donnees

### dim_ville

| Colonne | Type | Description |
|---|---|---|
| ville_sk | SERIAL | Cle primaire |
| ville_id | TEXT | Identifiant unique (ex: paris) |
| nom | TEXT | Nom de la ville |
| region | TEXT | Region administrative |
| latitude | NUMERIC | Coordonnee GPS |
| longitude | NUMERIC | Coordonnee GPS |

### dim_date

| Colonne | Type | Description |
|---|---|---|
| date_id | INTEGER | Cle au format YYYYMMDD |
| date | DATE | Date complete |
| annee | INTEGER | Annee |
| trimestre | INTEGER | Trimestre (1 a 4) |
| mois | INTEGER | Mois (1 a 12) |
| saison | TEXT | Hiver, Printemps, Ete, Automne |
| est_weekend | BOOLEAN | Vrai si samedi ou dimanche |

### fait_meteo

| Colonne | Type | Description |
|---|---|---|
| date_id | INTEGER | Cle etrangere vers dim_date |
| ville_id | TEXT | Cle etrangere vers dim_ville |
| temp_max_c | NUMERIC | Temperature maximale en C |
| temp_min_c | NUMERIC | Temperature minimale en C |
| temp_moy_c | NUMERIC | Temperature moyenne en C |
| precipitation_mm | NUMERIC | Precipitations en mm |
| vent_max_kmh | NUMERIC | Vitesse max du vent en km/h |
| description_meteo | TEXT | Description lisible du temps |

---

## Villes disponibles

| Ville | Region |
|---|---|
| Paris | Ile-de-France |
| Lyon | Auvergne-Rhone-Alpes |
| Marseille | PACA |
| Bordeaux | Nouvelle-Aquitaine |
| Lille | Hauts-de-France |
| Nantes | Pays de la Loire |

---

## Choix techniques

**Modele dimensionnel Kimball** : dim_ville + dim_date + fait_meteo permet
des requetes analytiques simples et performantes. Les jointures sont intuitives
pour les equipes metier.

**date_id au format YYYYMMDD** : entier plus rapide a joindre qu'une DATE,
lisible directement sans conversion.

**Upsert sur les 3 tables** : le pipeline peut etre relance sans creer de
doublons. Les donnees existantes sont mises a jour si l'API les corrige.

**SQLite en memoire pour les tests** : pas de dependance a PostgreSQL pour
faire tourner les tests. Isolation complete entre chaque test.

---

## Axes d'amelioration

- Ajout d'Apache Airflow pour planifier le pipeline (Phase 2)
- Deploiement sur AWS S3 + Athena (Phase 3)
- Ajout de nouvelles villes europeennes
- Dashboard Power BI ou Metabase sur les donnees

---

## Auteur

Rayane ilo