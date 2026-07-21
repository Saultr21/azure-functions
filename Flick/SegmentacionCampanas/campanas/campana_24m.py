from datetime import date

from models import RegistroCliente
from filtros_globales import cumple_filtros_globales
from dedup import deduplicar_por_matricula_ultima_visita
from utils import restar_meses_estilo_js


def filtrar_24m(registros: list[RegistroCliente], *, hoy: date) -> list[RegistroCliente]:
    """Réplica exacta de Fecha24MesesSinVisita(CSV).osts. Usa
    restar_meses_estilo_js (no relativedelta) para replicar el overflow de
    JS Date.setMonth — ver el fix aplicado en Task 7 tras revisión de código,
    que encontró que dateutil.relativedelta clampea en vez de desbordar."""
    corte = restar_meses_estilo_js(hoy, 24)

    candidatos = [
        r for r in registros
        if cumple_filtros_globales(r, aplica_fecha_minima=True, aplica_codigos_excluidos=True)
        and r.fecha_matriculacion is not None
        and r.fecha_servicio is not None
    ]

    deduplicados = deduplicar_por_matricula_ultima_visita(candidatos)

    finales = [r for r in deduplicados if r.fecha_servicio <= corte]

    return sorted(finales, key=lambda r: r.fecha_servicio)
