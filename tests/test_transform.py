# imports
import pytest
import pandas as pd
from src.transform import (
    construire_dim_ville,
    construire_dim_date,
    construire_fait_meteo,
    calculer_stats_mensuelles,
)

# Tests construire_dim_ville
def test_dim_ville_retourne_dataframe():
    result = construire_dim_ville(["Paris", "Lyon"])
    assert isinstance(result, pd.DataFrame)


def test_dim_ville_nombre_correct():
    result = construire_dim_ville(["Paris", "Lyon", "Marseille"])
    assert len(result) == 3


def test_dim_ville_colonnes_attendues():
    result = construire_dim_ville(["Paris"])
    for col in ["ville_id", "nom", "region", "pays", "latitude", "longitude"]:
        assert col in result.columns


def test_dim_ville_id_en_minuscule():
    result = construire_dim_ville(["Paris"])
    assert result["ville_id"].iloc[0] == "paris"


def test_dim_ville_liste_vide():
    result = construire_dim_ville([])
    assert len(result) == 0


# Tests construire_dim_date
def test_dim_date_retourne_dataframe():
    result = construire_dim_date("2024-01-01", "2024-01-07")
    assert isinstance(result, pd.DataFrame)


def test_dim_date_nombre_jours_correct():
    result = construire_dim_date("2024-01-01", "2024-01-31")
    assert len(result) == 31


def test_dim_date_colonnes_attendues():
    result = construire_dim_date("2024-01-01", "2024-01-01")
    for col in ["date_id", "annee", "mois", "trimestre", "saison", "est_weekend"]:
        assert col in result.columns


def test_dim_date_saison_hiver():
    result = construire_dim_date("2024-01-15", "2024-01-15")
    assert result["saison"].iloc[0] == "Hiver"


def test_dim_date_saison_ete():
    result = construire_dim_date("2024-07-15", "2024-07-15")
    assert result["saison"].iloc[0] == "Ete"


def test_dim_date_weekend_correct():
    # Le 6 janvier 2024 est un samedi
    result = construire_dim_date("2024-01-06", "2024-01-06")
    assert result["est_weekend"].iloc[0] == True


def test_dim_date_id_format_correct():
    # date_id doit etre au format YYYYMMDD
    result = construire_dim_date("2024-03-15", "2024-03-15")
    assert result["date_id"].iloc[0] == 20240315


# Tests construire_fait_meteo
def test_fait_meteo_retourne_dataframe(resultats_api):
    result = construire_fait_meteo(resultats_api)
    assert isinstance(result, pd.DataFrame)


def test_fait_meteo_nombre_lignes_correct(resultats_api):
    # Paris 3 jours + Lyon 3 jours + Marseille 2 jours = 8 lignes
    result = construire_fait_meteo(resultats_api)
    assert len(result) == 8


def test_fait_meteo_temperatures_aberrantes_exclues(resultats_api):
    # Les temperatures 999 et -999 de Marseille doivent etre None
    result = construire_fait_meteo(resultats_api)
    marseille = result[result["ville_id"] == "marseille"]
    assert pd.isna(marseille["temp_max_c"].iloc[0])
    assert pd.isna(marseille["temp_min_c"].iloc[0])


def test_fait_meteo_temperature_moyenne_calculee(resultats_api):
    # temp_moy = (temp_max + temp_min) / 2
    result = construire_fait_meteo(resultats_api)
    paris_j1 = result[(result["ville_id"] == "paris") & (result["date_id"] == 20240101)]
    assert paris_j1["temp_moy_c"].iloc[0] == round((9.6 + 5.7) / 2, 1)


def test_fait_meteo_liste_vide():
    result = construire_fait_meteo([])
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 0


def test_fait_meteo_ville_id_en_minuscule(resultats_api):
    result = construire_fait_meteo(resultats_api)
    assert result["ville_id"].str.islower().all()


# Tests calculer_stats_mensuelles
def test_stats_mensuelles_retourne_dataframe(fait_meteo_df, dim_date_df):
    result = calculer_stats_mensuelles(fait_meteo_df, dim_date_df)
    assert isinstance(result, pd.DataFrame)


def test_stats_mensuelles_dataframes_vides():
    result = calculer_stats_mensuelles(pd.DataFrame(), pd.DataFrame())
    assert len(result) == 0

