"""Filtros globales aplicados por las 5 campañas de segmentación.

Modelo y municipio se comprueban SIEMPRE (así lo hacen los 5 Office Scripts
originales). Fecha mínima de matriculación y códigos de servicio excluidos
son opcionales, parametrizables por campaña, porque no todas las campañas
en producción los aplican (p. ej. 3M y 16M no filtran por fecha mínima).
"""

from datetime import date

from models import RegistroCliente
from utils import limpiar_texto_modelo, normalizar_texto

MODELOS_VALIDOS = [
    "nmax", "xmax125", "xmax300", "tmax", "mt125", "mt07", "mt09", "tenere700",
]

MUNICIPIOS_VALIDOS = [
    "arucas", "firgas", "galdar", "ingenio", "moya", "las palmas",
    "santa brigida", "guia", "telde", "teror", "valleseco",
    "valsequillo", "vega de san mateo",
]

CODIGOS_SERVICIO_EXCLUIDOS = {"PRE", "YGR", "YIT"}

FECHA_MINIMA_MATRICULACION = date(2019, 1, 1)


def cumple_filtros_globales(
    registro: RegistroCliente,
    *,
    aplica_fecha_minima: bool,
    aplica_codigos_excluidos: bool,
) -> bool:
    """Determina si un registro supera los filtros comunes a todas las campañas.

    Modelo y municipio se comprueban siempre. Fecha mínima y códigos
    excluidos se activan o desactivan por campaña mediante los flags.
    """
    modelo_limpio = limpiar_texto_modelo(registro.descripcion)
    if not any(m in modelo_limpio for m in MODELOS_VALIDOS):
        return False

    municipio_norm = normalizar_texto(registro.municipio)
    if not any(m in municipio_norm for m in MUNICIPIOS_VALIDOS):
        return False

    if aplica_fecha_minima:
        if registro.fecha_matriculacion is None:
            return False
        if registro.fecha_matriculacion < FECHA_MINIMA_MATRICULACION:
            return False

    if aplica_codigos_excluidos:
        if registro.codigo_servicio.strip().upper() in CODIGOS_SERVICIO_EXCLUIDOS:
            return False

    return True
