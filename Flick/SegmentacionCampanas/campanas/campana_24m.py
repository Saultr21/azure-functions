from datetime import date

from models import RegistroCliente
from filtros_globales import cumple_filtros_globales, tiene_codigo_excluido
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
        if cumple_filtros_globales(r, aplica_fecha_minima=True)
        and r.fecha_matriculacion is not None
        and r.fecha_servicio is not None
    ]

    deduplicados = deduplicar_por_matricula_ultima_visita(candidatos)

    # El corte de fecha y el código excluido se aplican DESPUÉS del dedup,
    # igual que en Fecha24MesesSinVisita(CSV).osts: el dedup elige la
    # "última visita" sin tener en cuenta el código de servicio, y solo
    # entonces se descarta por corte de fecha o por código excluido.
    finales = [
        r for r in deduplicados
        if r.fecha_servicio <= corte and not tiene_codigo_excluido(r)
    ]

    return sorted(finales, key=lambda r: r.fecha_servicio)
