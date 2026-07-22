from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from azure.storage.blob import BlobSasPermissions

from blob_storage import subir_excel_y_generar_link, CONTENT_TYPE_XLSX

CONNECTION_STRING = "UseDevelopmentStorage=true"
CONTAINER = "csv-campanas"
NOMBRE_ARCHIVO = "FiltradoCampana3M_2026-07-21.xlsx"


@patch("blob_storage.generate_blob_sas", return_value="firma-sas-fake")
@patch("blob_storage.BlobServiceClient.from_connection_string")
def test_sube_el_excel_y_devuelve_url_con_sas(mock_from_conn, mock_generate_sas):
    mock_client = MagicMock()
    mock_from_conn.return_value = mock_client
    mock_blob_client = mock_client.get_blob_client.return_value
    mock_blob_client.url = "https://cuenta.blob.core.windows.net/csv-campanas/archivo.xlsx"
    mock_client.credential.account_key = "clave-fake"

    contenido_fake = b"contenido-excel-binario-fake"

    url = subir_excel_y_generar_link(
        excel_contenido=contenido_fake,
        nombre_archivo=NOMBRE_ARCHIVO,
        connection_string=CONNECTION_STRING,
        container=CONTAINER,
        horas_expiracion=24,
    )

    # La URL devuelta debe contener el token SAS mockeado.
    assert url.startswith("https://cuenta.blob.core.windows.net/csv-campanas/archivo.xlsx?")
    assert "firma-sas-fake" in url

    # El contenido subido debe ser exactamente los bytes del Excel,
    # y overwrite=True para permitir regenerar el enlace sin fallos.
    upload_args, upload_kwargs = mock_blob_client.upload_blob.call_args
    assert upload_args[0] == contenido_fake
    assert upload_kwargs["overwrite"] is True

    # content_type de Excel + disposition attachment (los navegadores no
    # pueden previsualizar un .xlsx, así que se ofrece como descarga directa
    # con el nombre de archivo correcto).
    content_settings = upload_kwargs["content_settings"]
    assert content_settings.content_type == CONTENT_TYPE_XLSX
    assert content_settings.content_disposition == f'attachment; filename="{NOMBRE_ARCHIVO}"'

    # Los parámetros del SAS son de solo lectura y están correctamente
    # acotados al blob y contenedor correspondientes: una regresión a
    # write=True o a un blob/contenedor incorrecto debe hacer fallar el test.
    sas_kwargs = mock_generate_sas.call_args.kwargs
    # BlobSasPermissions no define __eq__, así que se compara su
    # representación en cadena (p. ej. "r" para solo lectura).
    assert str(sas_kwargs["permission"]) == str(BlobSasPermissions(read=True))
    assert sas_kwargs["blob_name"] == NOMBRE_ARCHIVO
    assert sas_kwargs["container_name"] == CONTAINER

    expiry = sas_kwargs["expiry"]
    assert isinstance(expiry, datetime)
    ahora = datetime.now(timezone.utc)
    assert timedelta(hours=23) < (expiry - ahora) < timedelta(hours=25)
