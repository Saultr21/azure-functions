import json
import logging
import os
from datetime import datetime, timezone

import azure.functions as func

from campanas.motor import ejecutar_campana, CampanaNoSoportadaError
from blob_storage import subir_excel_y_generar_link

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.route(route="segmentar_campana", methods=["POST"])
def segmentar_campana(req: func.HttpRequest) -> func.HttpResponse:
    campana_id = req.params.get("campana")
    if not campana_id:
        return _error(400, "campana_requerida", "Falta el parámetro 'campana'.")

    excel_bytes = req.get_body()
    if not excel_bytes:
        return _error(400, "excel_vacio", "El cuerpo de la petición está vacío.")

    try:
        resultado = ejecutar_campana(campana_id, excel_bytes, hoy=datetime.now(timezone.utc).date())
    except CampanaNoSoportadaError:
        return _error(400, "campana_desconocida", f"Campaña no soportada: '{campana_id}'.")
    except Exception:
        logging.exception("segmentar_campana: error procesando el Excel (campaña=%s)", campana_id)
        return _error(500, "error_procesamiento", "No se pudo procesar el Excel maestro.")

    if resultado.municipios_no_reconocidos:
        logging.warning(
            "segmentar_campana: campaña=%s municipios_no_reconocidos=%s",
            campana_id, resultado.municipios_no_reconocidos,
        )

    if resultado.total_clientes == 0:
        return func.HttpResponse(
            json.dumps({
                "total_clientes": 0,
                "download_url": None,
                "nombre_archivo": None,
                "csv_contenido": "",
                "municipios_no_reconocidos": resultado.municipios_no_reconocidos,
            }),
            status_code=200,
            mimetype="application/json",
        )

    try:
        download_url = subir_excel_y_generar_link(
            excel_contenido=resultado.excel_contenido,
            nombre_archivo=resultado.nombre_archivo,
            connection_string=os.environ["BLOB_CONNECTION_STRING"],
            container=os.environ["BLOB_CONTAINER_NAME"],
            horas_expiracion=24,
        )
    except Exception:
        logging.exception("segmentar_campana: error subiendo el Excel a Blob Storage")
        return _error(500, "error_subida_excel", "No se pudo generar el enlace de descarga.")

    logging.info("segmentar_campana: campaña=%s total_clientes=%d", campana_id, resultado.total_clientes)

    return func.HttpResponse(
        json.dumps({
            "total_clientes": resultado.total_clientes,
            "download_url": download_url,
            "nombre_archivo": resultado.nombre_archivo,
            "csv_contenido": resultado.csv_contenido,
            "municipios_no_reconocidos": resultado.municipios_no_reconocidos,
        }),
        status_code=200,
        mimetype="application/json",
    )


def _error(status_code: int, codigo: str, mensaje: str) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({"codigo": codigo, "mensaje": mensaje}),
        status_code=status_code,
        mimetype="application/json",
    )


@app.route(route="SegmentacionCampanasFlick", auth_level=func.AuthLevel.FUNCTION)
def SegmentacionCampanasFlick(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')

    if name:
        return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )