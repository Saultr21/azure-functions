import json
import logging
import os
from datetime import datetime, timezone

import azure.functions as func

from campanas.motor import ejecutar_campana, CampanaNoSoportadaError
from blob_storage import subir_csv_y_generar_link

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

    if resultado.total_clientes == 0:
        return func.HttpResponse(
            json.dumps({"total_clientes": 0, "download_url": None}),
            status_code=200,
            mimetype="application/json",
        )

    try:
        download_url = subir_csv_y_generar_link(
            csv_contenido=resultado.csv_contenido,
            nombre_archivo=resultado.nombre_archivo,
            connection_string=os.environ["BLOB_CONNECTION_STRING"],
            container=os.environ["BLOB_CONTAINER_NAME"],
            horas_expiracion=24,
        )
    except Exception:
        logging.exception("segmentar_campana: error subiendo el CSV a Blob Storage")
        return _error(500, "error_subida_csv", "No se pudo generar el enlace de descarga.")

    logging.info("segmentar_campana: campaña=%s total_clientes=%d", campana_id, resultado.total_clientes)

    return func.HttpResponse(
        json.dumps({"total_clientes": resultado.total_clientes, "download_url": download_url}),
        status_code=200,
        mimetype="application/json",
    )


def _error(status_code: int, codigo: str, mensaje: str) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({"codigo": codigo, "mensaje": mensaje}),
        status_code=status_code,
        mimetype="application/json",
    )
