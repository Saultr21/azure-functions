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


def municipios_no_reconocidos(registros: list[RegistroCliente]) -> dict[str, int]:
    """Cuenta, entre los registros con un modelo Yamaha válido, cuántos tienen
    un municipio que no está en `MUNICIPIOS_VALIDOS`.

    No cambia el filtrado (esos registros se siguen descartando igual que
    siempre) -- solo hace visible cuántos clientes potenciales se están
    perdiendo por un municipio no reconocido (mudanza, error de escritura en
    el Excel, zona de servicio nueva, etc.), para que Flick pueda detectarlo
    sin tener que revisar el Excel a mano."""
    conteo: dict[str, int] = {}
    for registro in registros:
        modelo_limpio = limpiar_texto_modelo(registro.descripcion)
        if not any(m in modelo_limpio for m in MODELOS_VALIDOS):
            continue

        municipio_norm = normalizar_texto(registro.municipio)
        if any(m in municipio_norm for m in MUNICIPIOS_VALIDOS):
            continue

        clave = registro.municipio.strip() if registro.municipio and registro.municipio.strip() else "(vacío)"
        conteo[clave] = conteo.get(clave, 0) + 1

    return dict(sorted(conteo.items(), key=lambda item: (-item[1], item[0])))


def resumen_municipios_no_reconocidos(
    conteo: dict[str, int], *, tope: int = 10
) -> tuple[int, str]:
    """A partir del dict de `municipios_no_reconocidos`, devuelve el total y un
    resumen de texto YA calculados en Python.

    Se hace aquí, y no en el agente de Copilot Studio, porque los LLM no suman
    de forma fiable decenas de enteros: si se le pide al modelo que calcule el
    total a partir del JSON, el número sale distinto en cada ejecución. El
    agente solo debe repetir estos valores verbatim, igual que hace con
    `total_clientes`.

    El resumen lista hasta `tope` municipios (el dict ya viene ordenado de mayor
    a menor), y si hay más los agrega como "y N municipio(s) más".
    """
    total = sum(conteo.values())
    if not conteo:
        return 0, ""

    items = list(conteo.items())
    principales = items[:tope]
    resumen = "; ".join(f"{municipio}: {n}" for municipio, n in principales)

    restantes = len(items) - len(principales)
    if restantes > 0:
        resumen += f"; y {restantes} municipio(s) más"

    return total, resumen
