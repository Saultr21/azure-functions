"""Fixtures compartidas de test.

`function_app.py` lee BLOB_CONNECTION_STRING y BLOB_CONTAINER_NAME de
os.environ (nunca hardcodeadas, ver local.settings.json.example). En los
tests, `subir_csv_y_generar_link` se mockea, pero la lectura de estas
variables ocurre antes de esa llamada, así que necesitan existir en el
entorno de test aunque su valor real no importe.
"""

import os

import pytest


@pytest.fixture(autouse=True)
def _variables_entorno_blob(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BLOB_CONNECTION_STRING", "UseDevelopmentStorage=true")
    monkeypatch.setenv("BLOB_CONTAINER_NAME", "csv-campanas-test")
