import json
from unittest.mock import patch

import azure.functions as func

from function_app import segmentar_campana


def _request(campana: str | None, body: bytes = b"") -> func.HttpRequest:
    params = {"campana": campana} if campana else {}
    return func.HttpRequest(
        method="POST", url="/api/segmentar_campana", params=params, body=body
    )


def test_falta_parametro_campana_devuelve_400():
    respuesta = segmentar_campana(_request(campana=None, body=b"contenido"))
    assert respuesta.status_code == 400


def test_cuerpo_vacio_devuelve_400():
    respuesta = segmentar_campana(_request(campana="3M", body=b""))
    assert respuesta.status_code == 400


def test_campana_desconocida_devuelve_400():
    respuesta = segmentar_campana(_request(campana="NO-EXISTE", body=b"contenido"))
    assert respuesta.status_code == 400


@patch("function_app.subir_csv_y_generar_link", return_value="https://fake/url?sas=1")
@patch("function_app.ejecutar_campana")
def test_ejecucion_correcta_devuelve_200_con_link(mock_ejecutar, mock_subir):
    from campanas.motor import ResultadoCampana

    mock_ejecutar.return_value = ResultadoCampana(
        total_clientes=3, csv_contenido="a;b\n1;2", nombre_archivo="Filtrado.csv"
    )

    respuesta = segmentar_campana(_request(campana="3M", body=b"excel-binario"))

    assert respuesta.status_code == 200
    cuerpo = json.loads(respuesta.get_body())
    assert cuerpo["total_clientes"] == 3
    assert cuerpo["download_url"] == "https://fake/url?sas=1"


@patch("function_app.ejecutar_campana")
def test_error_generico_al_ejecutar_campana_devuelve_500(mock_ejecutar):
    mock_ejecutar.side_effect = Exception("boom")

    respuesta = segmentar_campana(_request(campana="3M", body=b"excel-binario"))

    assert respuesta.status_code == 500
    cuerpo = json.loads(respuesta.get_body())
    assert "codigo" in cuerpo
    assert "mensaje" in cuerpo
    assert "boom" not in cuerpo["mensaje"]


@patch("function_app.subir_csv_y_generar_link")
@patch("function_app.ejecutar_campana")
def test_cero_resultados_no_sube_a_blob_y_devuelve_download_url_null(mock_ejecutar, mock_subir):
    from campanas.motor import ResultadoCampana

    mock_ejecutar.return_value = ResultadoCampana(
        total_clientes=0, csv_contenido="", nombre_archivo="x.csv"
    )

    respuesta = segmentar_campana(_request(campana="3M", body=b"excel-binario"))

    assert respuesta.status_code == 200
    cuerpo = json.loads(respuesta.get_body())
    assert cuerpo["total_clientes"] == 0
    assert cuerpo["download_url"] is None
    mock_subir.assert_not_called()


@patch("function_app.subir_csv_y_generar_link")
@patch("function_app.ejecutar_campana")
def test_error_al_subir_a_blob_devuelve_500(mock_ejecutar, mock_subir):
    from campanas.motor import ResultadoCampana

    mock_ejecutar.return_value = ResultadoCampana(
        total_clientes=3, csv_contenido="a;b\n1;2", nombre_archivo="Filtrado.csv"
    )
    mock_subir.side_effect = Exception("blob-boom")

    respuesta = segmentar_campana(_request(campana="3M", body=b"excel-binario"))

    assert respuesta.status_code == 500
    cuerpo = json.loads(respuesta.get_body())
    assert "codigo" in cuerpo
    assert "mensaje" in cuerpo
    assert "blob-boom" not in cuerpo["mensaje"]
