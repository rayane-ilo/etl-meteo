# imports
import pytest
import pandas as pd
from sqlalchemy import create_engine, text

@pytest.fixture
def resultats_api():
    # Donnees brutes simulees comme si elles venaient de l'API Open-Meteo
    return [
        {
            "ville": "Paris",
            "data": {
                "daily": {
                    "time":                ["2024-01-01", "2024-01-02", "2024-01-03"],
                    "temperature_2m_max":  [9.6,  11.6, 8.2],
                    "temperature_2m_min":  [5.7,  9.7,  2.1],
                    "precipitation_sum":   [2.9,  13.2, 0.0],
                    "windspeed_10m_max":   [15.2, 22.1, 18.4],
                    "weathercode":         [61,   63,   1],
                }
            }
        },
        {
            "ville": "Lyon",
            "data": {
                "daily": {
                    "time":                ["2024-01-01", "2024-01-02", "2024-01-03"],
                    "temperature_2m_max":  [7.1,  8.3,  6.5],
                    "temperature_2m_min":  [2.3,  3.1,  1.8],
                    "precipitation_sum":   [0.0,  5.4,  1.2],
                    "windspeed_10m_max":   [12.0, 18.6, 14.2],
                    "weathercode":         [1,    61,   3],
                }
            }
        },
        {
            # Ville avec des valeurs manquantes et aberrantes
            "ville": "Marseille",
            "data": {
                "daily": {
                    "time":                ["2024-01-01", "2024-01-02"],
                    "temperature_2m_max":  [999.0, 15.2],
                    "temperature_2m_min":  [-999.0, 8.1],
                    "precipitation_sum":   [None, 0.0],
                    "windspeed_10m_max":   [None, 25.0],
                    "weathercode":         [None, 1],
                }
            }
        },
    ]


@pytest.fixture
def dim_ville_df():
    # DataFrame de la dimension ville
    return pd.DataFrame([
        {"ville_id": "paris",     "nom": "Paris",     "region": "Ile-de-France",        "pays": "France", "latitude": 48.85, "longitude": 2.35},
        {"ville_id": "lyon",      "nom": "Lyon",      "region": "Auvergne-Rhone-Alpes", "pays": "France", "latitude": 45.75, "longitude": 4.85},
        {"ville_id": "marseille", "nom": "Marseille", "region": "PACA",                 "pays": "France", "latitude": 43.30, "longitude": 5.38},
    ])


@pytest.fixture
def dim_date_df():
    # DataFrame de la dimension date sur 3 jours
    from src.transform import construire_dim_date
    return construire_dim_date("2024-01-01", "2024-01-03")


@pytest.fixture
def fait_meteo_df(resultats_api):
    # DataFrame de faits meteo construit depuis les donnees simulees
    from src.transform import construire_fait_meteo
    return construire_fait_meteo(resultats_api)


@pytest.fixture
def engine_test():
    # Base SQLite en memoire — creee et detruite pour chaque test
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE dim_ville (
                ville_sk   INTEGER PRIMARY KEY AUTOINCREMENT,
                ville_id   TEXT UNIQUE NOT NULL,
                nom        TEXT,
                region     TEXT,
                pays       TEXT,
                latitude   REAL,
                longitude  REAL
            )
        """))
        conn.execute(text("""
            CREATE TABLE dim_date (
                date_sk      INTEGER PRIMARY KEY AUTOINCREMENT,
                date_id      INTEGER UNIQUE NOT NULL,
                date         TEXT,
                annee        INTEGER,
                trimestre    INTEGER,
                mois         INTEGER,
                mois_nom     TEXT,
                semaine      INTEGER,
                jour         INTEGER,
                jour_semaine TEXT,
                est_weekend  INTEGER,
                saison       TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE fait_meteo (
                meteo_sk         INTEGER PRIMARY KEY AUTOINCREMENT,
                date_id          INTEGER NOT NULL,
                ville_id         TEXT NOT NULL,
                temp_max_c       REAL,
                temp_min_c       REAL,
                temp_moy_c       REAL,
                precipitation_mm REAL,
                vent_max_kmh     REAL,
                code_meteo       INTEGER,
                description_meteo TEXT,
                UNIQUE (date_id, ville_id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE pipeline_runs (
                run_id        INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date      TEXT,
                date_debut    TEXT,
                date_fin      TEXT,
                nb_villes     INTEGER,
                nb_jours      INTEGER,
                nb_inseres    INTEGER,
                nb_mis_a_jour INTEGER,
                duree_sec     REAL,
                statut        TEXT
            )
        """))
        conn.commit()
    yield engine
    engine.dispose()

