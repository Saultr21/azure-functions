from datetime import date

from models import RegistroCliente
from filtros_globales import cumple_filtros_globales, tiene_codigo_excluido
from dedup import deduplicar_por_matricula_ultima_visita
from utils import restar_meses_estilo_js


def filtrar_36m(registros: list[RegistroCliente], *, hoy: date) -> list[RegistroCliente]:
    """Implementada solo a partir del PDF (§5, Campaña 36M) — SIN script real
    de referencia. Validar manualmente antes de producción (spec §8). Usa
    restar_meses_estilo_js (no relativedelta) — ver fix de Task 7. Por
    consistencia con 24M (única campaña con script real que comparte esta
    forma), el código excluido se comprueba DESPUÉS de deduplicar — ver fix
    de Task 8. Confirmar este supuesto en la validación manual de Task 15."""
    corte = restar_meses_estilo_js(hoy, 36)

    candidatos = [
        r for r in registros
        if cumple_filtros_globales(r, aplica_fecha_minima=True)
        and r.fecha_matriculacion is not None
        and r.fecha_servicio is not None
    ]

    deduplicados = deduplicar_por_matricula_ultima_visita(candidatos)
    finales = [
        r for r in deduplicados
        if r.fecha_servicio <= corte and not tiene_codigo_excluido(r)
    ]

    return sorted(finales, key=lambda r: r.fecha_servicio)
