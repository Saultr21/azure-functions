import azure.functions as func
import logging
import json
import dateparser

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

DATEPARSER_LANGUAGES = ['es', 'en']
DATEPARSER_SETTINGS = {
    'DATE_ORDER': 'DMY',
    'PREFER_DAY_OF_MONTH': 'first',
    'RETURN_AS_TIMEZONE_AWARE': False,
}

@app.route(route="normalizar_fecha", methods=["GET", "POST"])
def normalizar_fecha(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('normalizar_fecha: solicitud recibida.')

    # Obtener el valor 'fecha' desde query string o body JSON
    fecha_raw = req.params.get('fecha')
    if not fecha_raw:
        try:
            req_body = req.get_json()
            fecha_raw = req_body.get('fecha')
        except (ValueError, AttributeError):
            pass

    if not fecha_raw:
        return func.HttpResponse(
            json.dumps({"error": "Falta el campo 'fecha'. Envíalo como query param (?fecha=...) o en el body JSON."}),
            status_code=400,
            mimetype="application/json"
        )

    fecha_parseada = dateparser.parse(str(fecha_raw), languages=DATEPARSER_LANGUAGES, settings=DATEPARSER_SETTINGS)

    if fecha_parseada is None:
        return func.HttpResponse(
            json.dumps({"error": f"No se pudo interpretar la fecha '{fecha_raw}'. Intenta con formatos como 01/02/2025, 1-febrero-25 o February 1 2025."}),
            status_code=400,
            mimetype="application/json"
        )

    fecha_normalizada = fecha_parseada.strftime("%d/%m/%Y")
    logging.info(f'normalizar_fecha: "{fecha_raw}" → "{fecha_normalizada}"')

    return func.HttpResponse(
        json.dumps({"fecha_original": fecha_raw, "fecha_normalizada": fecha_normalizada}),
        status_code=200,
        mimetype="application/json"
    )