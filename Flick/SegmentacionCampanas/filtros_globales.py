"""Filtros globales aplicados por las 5 campañas de segmentación.

Modelo y municipio se comprueban SIEMPRE (así lo hacen los 5 Office Scripts
originales). Fecha mínima de matriculación es opcional, parametrizable por
campaña, porque no todas las campañas en producción la aplican (p. ej. 3M y
16M no filtran por fecha mínima).

El filtro de código de servicio excluido NO forma parte de
`cumple_filtros_globales`: en los Office Scripts originales se aplica
DESPUÉS de la deduplicación por matrícula (junto al corte de fecha de
servicio), no antes. Aplicarlo antes del dedup haría que, si la visita más
reciente de una matrícula tiene un código excluido, el dedup recayera sobre
una visita anterior con código válido en su lugar -- en producción esa
matrícula se descarta por completo. Por eso `tiene_codigo_excluido` se
expone como función independiente, para llamarla tras el dedup.
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
) -> bool:
    """Determina si un registro supera los filtros PRE-dedup comunes a todas las campañas.

    Modelo y municipio se comprueban siempre. Fecha mínima se activa o
    desactiva por campaña mediante el flag. El código de servicio excluido
    NO se comprueba aquí -- ver `tiene_codigo_excluido`.
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

    return True


def tiene_codigo_excluido(registro: RegistroCliente) -> bool:
    """Determina si el código de servicio del registro está en la lista de excluidos.

    Se aplica DESPUÉS de la deduplicación por matrícula (ver docstring del
    módulo) -- no dentro de `cumple_filtros_globales`.
    """
    return registro.codigo_servicio.strip().upper() in CODIGOS_SERVICIO_EXCLUIDOS
