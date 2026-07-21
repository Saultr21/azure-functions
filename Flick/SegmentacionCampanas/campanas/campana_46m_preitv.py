from datetime import date

from models import RegistroCliente
from filtros_globales import cumple_filtros_globales, tiene_codigo_excluido
from dedup import deduplicar_por_matricula_ultima_visita
from utils import restar_meses_estilo_js


def filtrar_46m_preitv(registros: list[RegistroCliente], *, hoy: date) -> list[RegistroCliente]:
    """Implementada solo a partir del PDF (§5, Campaña 46M/Pre-ITV) — SIN
    script real de referencia. Validar manualmente antes de producción. Usa
    restar_meses_estilo_js (no relativedelta) — ver fix de Task 7. Código
    excluido comprobado DESPUÉS de deduplicar, por consistencia con 24M —
    ver fix de Task 8. Confirmar en la validación manual de Task 15."""
    corte = restar_meses_estilo_js(hoy, 46)

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
