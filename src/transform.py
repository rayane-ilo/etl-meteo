# imports
import pandas as pd
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


# Mapping des codes meteo vers des descriptions lisibles
CODES_METEO = {
    0:  "Ciel clair",
    1:  "Principalement clair",
    2:  "Partiellement nuageux",
    3:  "Couvert",
    45: "Brouillard",
    48: "Brouillard givrant",
    51: "Bruine legere",
    53: "Bruine moderee",
    55: "Bruine dense",
    61: "Pluie legere",
    63: "Pluie moderee",
    65: "Pluie forte",
    71: "Neige legere",
    73: "Neige moderee",
    75: "Neige forte",
    80: "Averses legeres",
    81: "Averses moderees",
    82: "Averses violentes",
    95: "Orage",
    99: "Orage avec grele",
}

# Mapping des mois vers les saisons
SAISONS = {
    12: "Hiver", 1: "Hiver",  2: "Hiver",
    3:  "Printemps", 4: "Printemps", 5: "Printemps",
    6:  "Ete", 7: "Ete", 8: "Ete",
    9:  "Automne", 10: "Automne", 11: "Automne",
}

# Coordonnees et informations des villes
INFOS_VILLES = {
    "Paris":     {"latitude": 48.85, "longitude": 2.35,  "region": "Ile-de-France",   "pays": "France"},
    "Lyon":      {"latitude": 45.75, "longitude": 4.85,  "region": "Auvergne-Rhone-Alpes", "pays": "France"},
    "Marseille": {"latitude": 43.30, "longitude": 5.38,  "region": "PACA",            "pays": "France"},
    "Bordeaux":  {"latitude": 44.84, "longitude": -0.58, "region": "Nouvelle-Aquitaine", "pays": "France"},
    "Lille":     {"latitude": 50.63, "longitude": 3.07,  "region": "Hauts-de-France", "pays": "France"},
    "Nantes":    {"latitude": 47.22, "longitude": -1.55, "region": "Pays de la Loire", "pays": "France"},
}


def construire_dim_ville(villes: list[str]) -> pd.DataFrame:
    # Construction de la dimension ville avec les informations geographiques
    lignes = []
    for ville in villes:
        infos = INFOS_VILLES.get(ville, {})
        lignes.append({
            "ville_id":  ville.lower().replace(" ", "_"),
            "nom":       ville,
            "region":    infos.get("region", ""),
            "pays":      infos.get("pays", "France"),
            "latitude":  infos.get("latitude"),
            "longitude": infos.get("longitude"),
        })

    df = pd.DataFrame(lignes)
    logger.info(f"dim_ville : {len(df)} villes")
    return df


def construire_dim_date(date_debut: str, date_fin: str) -> pd.DataFrame:
    # Construction de la dimension date avec toutes les proprietes calendaires
    dates = pd.date_range(start=date_debut, end=date_fin, freq="D")

    df = pd.DataFrame({
        "date_id":      dates.strftime("%Y%m%d").astype(int),
        "date":         dates.date,
        "annee":        dates.year,
        "trimestre":    dates.quarter,
        "mois":         dates.month,
        "mois_nom":     dates.strftime("%B"),
        "semaine":      dates.isocalendar().week.astype(int),
        "jour":         dates.day,
        "jour_semaine": dates.strftime("%A"),
        "est_weekend":  dates.dayofweek >= 5,
        "saison":       dates.month.map(SAISONS),
    })

    logger.info(f"dim_date : {len(df)} jours du {date_debut} au {date_fin}")
    return df


def construire_fait_meteo(resultats_api: list[dict]) -> pd.DataFrame:
    # Construction de la table de faits a partir des donnees brutes de l'API
    if not resultats_api:
        logger.warning("Aucun resultat API — retourne DataFrame vide")
        return pd.DataFrame()

    lignes = []

    for resultat in resultats_api:
        ville = resultat["ville"]
        daily = resultat["data"]["daily"]
        nb_jours = len(daily["time"])

        for i in range(nb_jours):
            date_str = daily["time"][i]

            # Extraction securisee de chaque valeur
            temp_max   = _extraire_valeur(daily, "temperature_2m_max", i)
            temp_min   = _extraire_valeur(daily, "temperature_2m_min", i)
            precip     = _extraire_valeur(daily, "precipitation_sum", i)
            vent_max   = _extraire_valeur(daily, "windspeed_10m_max", i)
            code_meteo = _extraire_valeur(daily, "weathercode", i)

            # Calcul de la temperature moyenne
            temp_moy = None
            if temp_max is not None and temp_min is not None:
                temp_moy = round((temp_max + temp_min) / 2, 1)

            lignes.append({
                # Cles etrangeres vers les dimensions
                "date_id":      int(date_str.replace("-", "")),
                "ville_id":     ville.lower().replace(" ", "_"),
                # Mesures meteorologiques
                "temp_max_c":   temp_max,
                "temp_min_c":   temp_min,
                "temp_moy_c":   temp_moy,
                "precipitation_mm": precip,
                "vent_max_kmh": vent_max,
                "code_meteo":   int(code_meteo) if code_meteo is not None else None,
                "description_meteo": CODES_METEO.get(
                    int(code_meteo) if code_meteo is not None else -1, "Inconnu"
                ),
            })

    df = pd.DataFrame(lignes)
    n_avant = len(df)

    # Suppression des lignes sans date ou sans ville
    df = df.dropna(subset=["date_id", "ville_id"])

    # Validation des temperatures
    for col in ["temp_max_c", "temp_min_c", "temp_moy_c"]:
        df[col] = df[col].where(
            (df[col] >= -60) & (df[col] <= 60), other=None
        )

    # Validation des precipitations
    df["precipitation_mm"] = df["precipitation_mm"].where(
        (df["precipitation_mm"] >= 0) & (df["precipitation_mm"] <= 500),
        other=None
    )

    logger.info(f"fait_meteo : {len(df)} lignes ({n_avant - len(df)} exclues)")
    return df.reset_index(drop=True)


def calculer_stats_mensuelles(fait_meteo: pd.DataFrame, dim_date: pd.DataFrame) -> pd.DataFrame:
    # Calcul des statistiques meteorologiques par ville et par mois
    if fait_meteo.empty or dim_date.empty:
        return pd.DataFrame()

    # Jointure avec dim_date pour avoir le mois et l'annee
    df = fait_meteo.merge(
        dim_date[["date_id", "annee", "mois", "mois_nom", "saison"]],
        on="date_id",
        how="left",
    )

    return (
        df.groupby(["ville_id", "annee", "mois", "mois_nom", "saison"])
        .agg(
            temp_moy_mois     = ("temp_moy_c", "mean"),
            temp_max_mois     = ("temp_max_c", "max"),
            temp_min_mois     = ("temp_min_c", "min"),
            total_precip_mm   = ("precipitation_mm", "sum"),
            nb_jours_pluie    = ("precipitation_mm", lambda x: (x > 0).sum()),
            vent_max_mois     = ("vent_max_kmh", "max"),
        )
        .round(2)
        .reset_index()
        .sort_values(["ville_id", "annee", "mois"])
    )


def _extraire_valeur(daily: dict, cle: str, index: int):
    # Extraction securisee d'une valeur dans le dict daily de l'API
    valeurs = daily.get(cle, [])
    if index < len(valeurs) and valeurs[index] is not None:
        try:
            return float(valeurs[index])
        except (ValueError, TypeError):
            return None
    return None
