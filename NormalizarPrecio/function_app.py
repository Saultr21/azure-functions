import azure.functions as func
import logging
import re

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="normalizar_precio")
def normalizar_precio(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    precio = req.params.get('precio')
    if not precio:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            precio = req_body.get('precio')

    if precio is not None:
        precio_normalizado = re.sub(r'[^0-9,]', '', precio)
        logging.info(f'Precio normalizado: {precio_normalizado}')
        return func.HttpResponse(precio_normalizado, status_code=200)
    else:
        return func.HttpResponse(
            "Pasa el parámetro 'precio' en la query string o en el cuerpo JSON. "
            "Ejemplo: ?precio=euro%20100,%2000",
            status_code=400
        )