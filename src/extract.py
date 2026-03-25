# imports
import requests
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

# URL de base de l'API Open-Meteo
# Endpoint historique — donnees depuis 1940
API_BASE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Villes francaises avec leurs coordonnees GPS
VILLES = {
    "Paris":     {"latitude": 48.85, "longitude": 2.35},
    "Lyon":      {"latitude": 45.75, "longitude": 4.85},
    "Marseille": {"latitude": 43.30, "longitude": 5.38},
    "Bordeaux":  {"latitude": 44.84, "longitude": -0.58},
    "Lille":     {"latitude": 50.63, "longitude": 3.07},
    "Nantes":    {"latitude": 47.22, "longitude": -1.55},
}

# Variables meteorologiques a extraire
VARIABLES = [
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "windspeed_10m_max",
    "weathercode",
]


def fetch_meteo_ville(
    ville: str,
    date_debut: str,
    date_fin: str,
) -> Optional[dict]:
    # Recuperation des donnees meteo pour une ville sur une periode donnee
    coords = VILLES.get(ville)
    if not coords:
        logger.error(f"Ville inconnue : {ville}")
        return None

    logger.info(f"Extraction meteo — {ville} du {date_debut} au {date_fin}")

    try:
        response = requests.get(
            API_BASE_URL,
            params=[
                ("latitude",   coords["latitude"]),
                ("longitude",  coords["longitude"]),
                ("daily",      "temperature_2m_max"),
                ("daily",      "temperature_2m_min"),
                ("daily",      "precipitation_sum"),
                ("daily",      "windspeed_10m_max"),
                ("daily",      "weathercode"),
                ("start_date", date_debut),
                ("end_date",   date_fin),
                ("timezone",   "Europe/Paris"),
            ],
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

    except requests.exceptions.Timeout:
        logger.warning(f"Timeout pour {ville} — skip")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"Erreur HTTP pour {ville} : {e}")
        raise

    logger.info(f"{ville} : {len(data['daily']['time'])} jours recuperes")
    return {"ville": ville, "data": data}


def fetch_meteo_toutes_villes(
    date_debut: str,
    date_fin: str,
    villes: Optional[list] = None,
) -> list[dict]:
    # Extraction pour toutes les villes ou une liste specifique
    villes_cibles = villes or list(VILLES.keys())
    resultats = []

    for ville in villes_cibles:
        resultat = fetch_meteo_ville(ville, date_debut, date_fin)
        if resultat:
            resultats.append(resultat)
        # Pause de politesse entre chaque appel
        time.sleep(0.3)

    logger.info(f"Extraction terminee : {len(resultats)} villes")
    return resultats

