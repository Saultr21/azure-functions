from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from blob_storage import subir_csv_y_generar_link

CONNECTION_STRING = "UseDevelopmentStorage=true"
CONTAINER = "csv-campanas"


@patch("blob_storage.generate_blob_sas", return_value="firma-sas-fake")
@patch("blob_storage.BlobServiceClient.from_connection_string")
def test_sube_el_csv_y_devuelve_url_con_sas(mock_from_conn, mock_generate_sas):
    mock_client = MagicMock()
    mock_from_conn.return_value = mock_client
    mock_blob_client = mock_client.get_blob_client.return_value
    mock_blob_client.url = "https://cuenta.blob.core.windows.net/csv-campanas/archivo.csv"
    mock_client.credential.account_key = "clave-fake"

    url = subir_csv_y_generar_link(
        csv_contenido="a;b\n1;2",
        nombre_archivo="FiltradoCampana3M_2026-07-21.csv",
        connection_string=CONNECTION_STRING,
        container=CONTAINER,
        horas_expiracion=24,
    )

    mock_blob_client.upload_blob.assert_called_once()
    assert url.startswith("https://cuenta.blob.core.windows.net/csv-campanas/archivo.csv?")
    assert "firma-sas-fake" in url
