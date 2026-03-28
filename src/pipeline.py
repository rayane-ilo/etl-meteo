# imports
import logging
import time
from datetime import date
from dotenv import load_dotenv

from src.extract import fetch_meteo_toutes_villes, VILLES
from src.transform import (
    construire_dim_ville,
    construire_dim_date,
    construire_fait_meteo,
    calculer_stats_mensuelles,
)
from src.load import (
    get_engine,
    initialiser_schema,
    upsert_dim_ville,
    upsert_dim_date,
    upsert_fait_meteo,
    logger_run,
)

load_dotenv()

# Configuration des logs vers le terminal et un fichier
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"logs/pipeline_{date.today()}.log"),
    ],
)
logger = logging.getLogger("pipeline")


def run_pipeline(
    date_debut: str,
    date_fin: str,
    villes: list = None,
) -> dict:
    # Orchestration complete du pipeline ETL meteo
    villes_cibles = villes or list(VILLES.keys())

    logger.info(f"=== PIPELINE DEMARRE — {date_debut} au {date_fin} ===")
    logger.info(f"Villes : {villes_cibles}")
    debut = time.perf_counter()

    # Preparation des metriques du run
    metriques = {
        "run_date":     date.today(),
        "date_debut":   date_debut,
        "date_fin":     date_fin,
        "nb_villes":    len(villes_cibles),
        "nb_jours":     0,
        "nb_inseres":   0,
        "nb_mis_a_jour": 0,
        "duree_sec":    0,
        "statut":       "echec",
    }

    engine = get_engine()
    initialiser_schema(engine)

    try:
        # Etape 1 : extraction
        logger.info("Etape 1/4 : Extraction API")
        resultats = fetch_meteo_toutes_villes(date_debut, date_fin, villes_cibles)

        if not resultats:
            logger.warning("Aucun resultat — arret du pipeline")
            return metriques

        # Etape 2 : transformation
        logger.info("Etape 2/4 : Transformation")
        dim_ville  = construire_dim_ville(villes_cibles)
        dim_date   = construire_dim_date(date_debut, date_fin)
        fait_meteo = construire_fait_meteo(resultats)

        metriques["nb_jours"] = len(dim_date)

        # Etape 3 : chargement
        logger.info("Etape 3/4 : Chargement PostgreSQL")
        r_ville  = upsert_dim_ville(dim_ville, engine)
        r_date   = upsert_dim_date(dim_date, engine)
        r_meteo  = upsert_fait_meteo(fait_meteo, engine)

        metriques["nb_inseres"]    = r_meteo["inseres"]
        metriques["nb_mis_a_jour"] = r_meteo["mis_a_jour"]

        # Etape 4 : rapport
        logger.info("Etape 4/4 : Rapport")
        stats = calculer_stats_mensuelles(fait_meteo, dim_date)
        if not stats.empty:
            logger.info(f"Stats mensuelles :\n{stats.to_string(index=False)}")

        metriques["statut"] = "succes"

    except Exception as e:
        logger.error(f"Pipeline echoue : {e}", exc_info=True)
        metriques["statut"] = "echec"
        raise

    finally:
        # Enregistrement des metriques dans tous les cas
        metriques["duree_sec"] = round(time.perf_counter() - debut, 3)
        logger_run(engine, metriques)
        logger.info(
            f"=== PIPELINE TERMINE en {metriques['duree_sec']}s — "
            f"{metriques['nb_inseres']} inseres, "
            f"{metriques['nb_mis_a_jour']} mis a jour ==="
        )

    return metriques


# Point d'entree — uniquement quand lance directement
if __name__ == "__main__":
    run_pipeline(
        date_debut="2024-01-01",
        date_fin="2024-03-31",
        villes=["Paris", "Lyon", "Marseille", "Bordeaux"],
    )

