# imports
import pytest
import pandas as pd
from datetime import date
from sqlalchemy import text
from src.load import upsert_dim_ville, upsert_dim_date, upsert_fait_meteo, logger_run

# Tests upsert_dim_ville
def test_upsert_dim_ville_insere(dim_ville_df, engine_test):
    result = upsert_dim_ville(dim_ville_df, engine_test)
    assert result["inseres"] == 3
    assert result["mis_a_jour"] == 0


def test_upsert_dim_ville_met_a_jour(dim_ville_df, engine_test):
    upsert_dim_ville(dim_ville_df, engine_test)
    result = upsert_dim_ville(dim_ville_df, engine_test)
    assert result["inseres"] == 0
    assert result["mis_a_jour"] == 3


def test_upsert_dim_ville_pas_de_doublons(dim_ville_df, engine_test):
    upsert_dim_ville(dim_ville_df, engine_test)
    upsert_dim_ville(dim_ville_df, engine_test)
    with engine_test.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM dim_ville")).scalar()
    assert count == 3


def test_upsert_dim_ville_vide(engine_test):
    result = upsert_dim_ville(pd.DataFrame(), engine_test)
    assert result["inseres"] == 0


# Tests upsert_dim_date
def test_upsert_dim_date_insere(dim_date_df, engine_test):
    result = upsert_dim_date(dim_date_df, engine_test)
    assert result["inseres"] == 3
    assert result["mis_a_jour"] == 0


def test_upsert_dim_date_pas_de_doublons(dim_date_df, engine_test):
    upsert_dim_date(dim_date_df, engine_test)
    upsert_dim_date(dim_date_df, engine_test)
    with engine_test.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM dim_date")).scalar()
    assert count == 3


# Tests upsert_fait_meteo
def test_upsert_fait_meteo_insere(fait_meteo_df, engine_test):
    result = upsert_fait_meteo(fait_meteo_df, engine_test)
    assert result["inseres"] == len(fait_meteo_df)
    assert result["mis_a_jour"] == 0


def test_upsert_fait_meteo_met_a_jour(fait_meteo_df, engine_test):
    upsert_fait_meteo(fait_meteo_df, engine_test)
    result = upsert_fait_meteo(fait_meteo_df, engine_test)
    assert result["inseres"] == 0
    assert result["mis_a_jour"] == len(fait_meteo_df)


def test_upsert_fait_meteo_pas_de_doublons(fait_meteo_df, engine_test):
    upsert_fait_meteo(fait_meteo_df, engine_test)
    upsert_fait_meteo(fait_meteo_df, engine_test)
    with engine_test.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM fait_meteo")).scalar()
    assert count == len(fait_meteo_df)


def test_upsert_fait_meteo_vide(engine_test):
    result = upsert_fait_meteo(pd.DataFrame(), engine_test)
    assert result["inseres"] == 0


# Tests logger_run
def test_logger_run_enregistre(engine_test):
    info = {
        "run_date":      date.today(),
        "date_debut":    "2024-01-01",
        "date_fin":      "2024-03-31",
        "nb_villes":     4,
        "nb_jours":      91,
        "nb_inseres":    364,
        "nb_mis_a_jour": 0,
        "duree_sec":     3.3,
        "statut":        "succes",
    }
    logger_run(engine_test, info)
    with engine_test.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM pipeline_runs")).scalar()
    assert count == 1

