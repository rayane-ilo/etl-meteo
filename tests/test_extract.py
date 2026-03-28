# imports
import pytest
from unittest.mock import patch, MagicMock
from src.extract import fetch_meteo_ville, fetch_meteo_toutes_villes

# Tests fetch_meteo_ville avec mock
def test_fetch_meteo_ville_retourne_dict():
    reponse = MagicMock()
    reponse.json.return_value = {
        "daily": {
            "time": ["2024-01-01"],
            "temperature_2m_max": [9.6],
        }
    }
    reponse.raise_for_status = MagicMock()

    with patch("src.extract.requests.get", return_value=reponse):
        result = fetch_meteo_ville("Paris", "2024-01-01", "2024-01-01")

    assert isinstance(result, dict)
    assert result["ville"] == "Paris"
    assert "data" in result


def test_fetch_meteo_ville_inconnue():
    # Une ville inconnue doit retourner None
    result = fetch_meteo_ville("VilleInconnue", "2024-01-01", "2024-01-01")
    assert result is None


def test_fetch_meteo_ville_timeout_retourne_none():
    import requests as req
    with patch("src.extract.requests.get", side_effect=req.exceptions.Timeout):
        result = fetch_meteo_ville("Paris", "2024-01-01", "2024-01-01")
    assert result is None


def test_fetch_meteo_toutes_villes_retourne_liste():
    reponse = MagicMock()
    reponse.json.return_value = {
        "daily": {"time": ["2024-01-01"], "temperature_2m_max": [9.6]}
    }
    reponse.raise_for_status = MagicMock()

    with patch("src.extract.requests.get", return_value=reponse):
        result = fetch_meteo_toutes_villes("2024-01-01", "2024-01-01", ["Paris", "Lyon"])

    assert isinstance(result, list)
    assert len(result) == 2


def test_fetch_meteo_toutes_villes_liste_vide():
    # Une liste vide utilise toutes les villes par defaut
    # On mock pour ne pas faire de vrai appel API
    reponse = MagicMock()
    reponse.json.return_value = {
        "daily": {"time": ["2024-01-01"], "temperature_2m_max": [9.6]}
    }
    reponse.raise_for_status = MagicMock()

    with patch("src.extract.requests.get", return_value=reponse):
        result = fetch_meteo_toutes_villes("2024-01-01", "2024-01-01", [])

    # Liste vide = toutes les villes = 6 villes
    assert len(result) == 6

