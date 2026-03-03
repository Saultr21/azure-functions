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
        # Extraer solo dígitos, puntos y comas
        solo_numerico = re.sub(r'[^0-9.,]', '', precio)

        # Detectar formato y normalizar a coma como separador decimal
        # Caso: separador decimal es punto  → "118.13"  o "1.000.13" → convertir a "118,13"
        # Caso: separador decimal es coma   → "118,13"  o "1.000,13" → mantener coma
        if re.search(r'\.\d{1,2}$', solo_numerico):
            # El punto es separador decimal: quitar separadores de miles y usar coma para decimales
            partes = solo_numerico.rsplit('.', 1)
            entero = partes[0].replace(',', '').replace('.', '')
            decimal = partes[1] if len(partes) > 1 else ''
            precio_normalizado = f"{entero},{decimal}" if decimal else entero
        elif re.search(r',\d{1,2}$', solo_numerico):
            # El separador decimal ya es coma: quitar puntos de miles
            partes = solo_numerico.rsplit(',', 1)
            entero = partes[0].replace('.', '').replace(',', '')
            decimal = partes[1] if len(partes) > 1 else ''
            precio_normalizado = f"{entero},{decimal}" if decimal else entero
        else:
            # Sin decimales: quitar cualquier separador de miles
            precio_normalizado = solo_numerico.replace('.', '').replace(',', '')

        logging.info(f'Precio normalizado: {precio_normalizado}')
        return func.HttpResponse(precio_normalizado, status_code=200)
    else:
        return func.HttpResponse(
            "0",
            mimetype="application/json",
            status_code=200
        )