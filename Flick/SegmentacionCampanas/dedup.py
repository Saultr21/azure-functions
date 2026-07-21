from datetime import date

from models import RegistroCliente


def deduplicar_por_matricula_ultima_visita(
    registros: list[RegistroCliente],
) -> list[RegistroCliente]:
    """Usado por 3M, 24M, 36M, 46M: si hay varias visitas de la misma
    matrícula, se conserva la de fecha_servicio más reciente."""
    por_matricula: dict[str, RegistroCliente] = {}
    for r in registros:
        actual = por_matricula.get(r.matricula)
        fecha_actual = actual.fecha_servicio if actual else None
        fecha_nueva = r.fecha_servicio
        if actual is None or _es_mas_reciente(fecha_nueva, fecha_actual):
            por_matricula[r.matricula] = r
    return list(por_matricula.values())


def deduplicar_por_matricula_ultima_fila(
    registros: list[RegistroCliente],
) -> list[RegistroCliente]:
    """Usado por 16M: se queda con la última fila del Excel para esa
    matrícula, sin comparar fechas (así lo hace el .osts real: un Map que se
    sobreescribe según el orden de lectura)."""
    por_matricula: dict[str, RegistroCliente] = {}
    for r in registros:
        por_matricula[r.matricula] = r
    return list(por_matricula.values())


def _es_mas_reciente(candidata: date | None, actual: date | None) -> bool:
    if candidata is None:
        return False
    if actual is None:
        return True
    return candidata > actual
