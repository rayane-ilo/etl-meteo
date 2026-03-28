# imports
import os
import logging
import pandas as pd
from datetime import date
from contextlib import contextmanager
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
logger = logging.getLogger(__name__)


def get_engine():
    # Creation du moteur SQLAlchemy depuis les variables d'environnement
    url = (
        f"postgresql://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}"
        f"@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']}"
    )
    return create_engine(url, pool_pre_ping=True)


@contextmanager
def get_conn(engine):
    # Gestionnaire de contexte pour les transactions
    conn = engine.connect()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Transaction annulee : {e}")
        raise
    finally:
        conn.close()


def initialiser_schema(engine):
    # Creation des tables si elles n'existent pas
    with get_conn(engine) as conn:

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dim_ville (
                ville_sk    SERIAL PRIMARY KEY,
                ville_id    TEXT UNIQUE NOT NULL,
                nom         TEXT,
                region      TEXT,
                pays        TEXT,
                latitude    NUMERIC(8,4),
                longitude   NUMERIC(8,4),
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dim_date (
                date_sk      SERIAL PRIMARY KEY,
                date_id      INTEGER UNIQUE NOT NULL,
                date         DATE,
                annee        INTEGER,
                trimestre    INTEGER,
                mois         INTEGER,
                mois_nom     TEXT,
                semaine      INTEGER,
                jour         INTEGER,
                jour_semaine TEXT,
                est_weekend  BOOLEAN,
                saison       TEXT,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS fait_meteo (
                meteo_sk          SERIAL PRIMARY KEY,
                date_id           INTEGER NOT NULL,
                ville_id          TEXT NOT NULL,
                temp_max_c        NUMERIC(5,1),
                temp_min_c        NUMERIC(5,1),
                temp_moy_c        NUMERIC(5,1),
                precipitation_mm  NUMERIC(6,1),
                vent_max_kmh      NUMERIC(5,1),
                code_meteo        INTEGER,
                description_meteo TEXT,
                created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (date_id, ville_id)
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                run_id        SERIAL PRIMARY KEY,
                run_date      DATE NOT NULL,
                date_debut    TEXT,
                date_fin      TEXT,
                nb_villes     INTEGER,
                nb_jours      INTEGER,
                nb_inseres    INTEGER,
                nb_mis_a_jour INTEGER,
                duree_sec     NUMERIC(8,3),
                statut        TEXT,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

    logger.info("Schema verifie : dim_ville, dim_date, fait_meteo, pipeline_runs")


def upsert_dim_ville(df: pd.DataFrame, engine) -> dict:
    # Upsert de la dimension ville
    if df.empty:
        return {"inseres": 0, "mis_a_jour": 0}

    inseres = mis_a_jour = 0

    with get_conn(engine) as conn:
        for _, row in df.iterrows():
            data = {k: (None if pd.isna(v) else v) for k, v in row.items()}

            existing = conn.execute(
                text("SELECT ville_sk FROM dim_ville WHERE ville_id = :ville_id"),
                {"ville_id": data["ville_id"]}
            ).fetchone()

            if existing:
                conn.execute(text("""
                    UPDATE dim_ville SET
                        nom=:nom, region=:region, pays=:pays,
                        latitude=:latitude, longitude=:longitude
                    WHERE ville_id=:ville_id
                """), data)
                mis_a_jour += 1
            else:
                conn.execute(text("""
                    INSERT INTO dim_ville
                        (ville_id, nom, region, pays, latitude, longitude)
                    VALUES
                        (:ville_id, :nom, :region, :pays, :latitude, :longitude)
                """), data)
                inseres += 1

    logger.info(f"dim_ville : {inseres} inseres, {mis_a_jour} mis a jour")
    return {"inseres": inseres, "mis_a_jour": mis_a_jour}


def upsert_dim_date(df: pd.DataFrame, engine) -> dict:
    # Upsert de la dimension date
    if df.empty:
        return {"inseres": 0, "mis_a_jour": 0}

    inseres = mis_a_jour = 0

    with get_conn(engine) as conn:
        for _, row in df.iterrows():
            data = {k: (None if pd.isna(v) else v) for k, v in row.items()}

            # Conversion du type date pour PostgreSQL
            if data.get("date"):
                data["date"] = str(data["date"])

            existing = conn.execute(
                text("SELECT date_sk FROM dim_date WHERE date_id = :date_id"),
                {"date_id": data["date_id"]}
            ).fetchone()

            if existing:
                mis_a_jour += 1
            else:
                conn.execute(text("""
                    INSERT INTO dim_date
                        (date_id, date, annee, trimestre, mois, mois_nom,
                         semaine, jour, jour_semaine, est_weekend, saison)
                    VALUES
                        (:date_id, :date, :annee, :trimestre, :mois, :mois_nom,
                         :semaine, :jour, :jour_semaine, :est_weekend, :saison)
                """), data)
                inseres += 1

    logger.info(f"dim_date : {inseres} inseres, {mis_a_jour} mis a jour")
    return {"inseres": inseres, "mis_a_jour": mis_a_jour}


def upsert_fait_meteo(df: pd.DataFrame, engine) -> dict:
    # Upsert de la table de faits meteo
    if df.empty:
        return {"inseres": 0, "mis_a_jour": 0}

    inseres = mis_a_jour = 0

    with get_conn(engine) as conn:
        for _, row in df.iterrows():
            data = {k: (None if pd.isna(v) else v) for k, v in row.items()}

            existing = conn.execute(
                text("""
                    SELECT meteo_sk FROM fait_meteo
                    WHERE date_id=:date_id AND ville_id=:ville_id
                """),
                {"date_id": data["date_id"], "ville_id": data["ville_id"]}
            ).fetchone()

            if existing:
                conn.execute(text("""
                    UPDATE fait_meteo SET
                        temp_max_c=:temp_max_c,
                        temp_min_c=:temp_min_c,
                        temp_moy_c=:temp_moy_c,
                        precipitation_mm=:precipitation_mm,
                        vent_max_kmh=:vent_max_kmh,
                        code_meteo=:code_meteo,
                        description_meteo=:description_meteo
                    WHERE date_id=:date_id AND ville_id=:ville_id
                """), data)
                mis_a_jour += 1
            else:
                conn.execute(text("""
                    INSERT INTO fait_meteo (
                        date_id, ville_id, temp_max_c, temp_min_c,
                        temp_moy_c, precipitation_mm, vent_max_kmh,
                        code_meteo, description_meteo
                    ) VALUES (
                        :date_id, :ville_id, :temp_max_c, :temp_min_c,
                        :temp_moy_c, :precipitation_mm, :vent_max_kmh,
                        :code_meteo, :description_meteo
                    )
                """), data)
                inseres += 1

    logger.info(f"fait_meteo : {inseres} inseres, {mis_a_jour} mis a jour")
    return {"inseres": inseres, "mis_a_jour": mis_a_jour}


def logger_run(engine, info: dict):
    # Enregistrement des metriques du run dans pipeline_runs
    with get_conn(engine) as conn:
        conn.execute(text("""
            INSERT INTO pipeline_runs
                (run_date, date_debut, date_fin, nb_villes, nb_jours,
                 nb_inseres, nb_mis_a_jour, duree_sec, statut)
            VALUES
                (:run_date, :date_debut, :date_fin, :nb_villes, :nb_jours,
                 :nb_inseres, :nb_mis_a_jour, :duree_sec, :statut)
        """), info)
    logger.info(f"Run enregistre : {info['statut']}")

