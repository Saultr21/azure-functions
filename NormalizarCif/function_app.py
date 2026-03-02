import azure.functions as func
import logging
import re
import json

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


def _normalizar_cif(valor: str) -> str:
    """
    Normaliza un NIF/NIE/CIF español eliminando separadores (puntos, guiones,
    espacios y cualquier otro carácter no alfanumérico) y convirtiendo a
    mayúsculas.

    Ejemplos:
        "78.503.471-D"  ->  "78503471D"
        "X-1234567-Z"   ->  "X1234567Z"
        "B-12.345.678"  ->  "B12345678"
        " 12 345 678 Z" ->  "12345678Z"
    """
    if not valor:
        return ""
    # Eliminar todo lo que no sea letra o dígito
    normalizado = re.sub(r"[^A-Za-z0-9]", "", valor)
    return normalizado.upper()


@app.route(route="normalizar_cif")
def normalizar_cif(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("NormalizarCif: solicitud recibida.")

    # Aceptar el valor por query string o por cuerpo JSON
    # Parámetros soportados: "cif", "nif", "nie", "value"
    _PARAM_NAMES = ("cif", "nif", "nie", "value")

    valor = None
    for param in _PARAM_NAMES:
        valor = req.params.get(param)
        if valor:
            break

    if not valor:
        try:
            body = req.get_json()
        except ValueError:
            body = {}
        for param in _PARAM_NAMES:
            valor = body.get(param)
            if valor:
                break

    if not valor:
        return func.HttpResponse(
            "{}",
            mimetype="application/json",
            status_code=200
        )

    resultado = _normalizar_cif(str(valor))

    # Advertencia si el resultado supera 10 caracteres (límite habitual en SharePoint/Excel)
    advertencia = None
    if len(resultado) > 10:
        advertencia = (
            f"El valor normalizado tiene {len(resultado)} caracteres, "
            "que supera el límite de 10."
        )
        logging.warning("NormalizarCif: %s", advertencia)

    respuesta = {"resultado": resultado, "longitud": len(resultado)}
    if advertencia:
        respuesta["advertencia"] = advertencia

    logging.info("NormalizarCif: '%s' -> '%s'", valor, resultado)

    return func.HttpResponse(
        json.dumps(respuesta),
        status_code=200,
        mimetype="application/json"
    )