# Flick/SegmentacionCampanas/campanas/campana_3m.py
from datetime import date

from dateutil.relativedelta import relativedelta

from models import RegistroCliente
from filtros_globales import cumple_filtros_globales
from dedup import deduplicar_por_matricula_ultima_visita

KM_MAXIMO_ULTIMO_SERVICIO = 200


def filtrar_3m(registros: list[RegistroCliente], *, hoy: date) -> list[RegistroCliente]:
    """Réplica exacta de FiltrarSinVisita3Meses(csv).osts: NO aplica fecha
    mínima 2019 ni códigos excluidos (ver tabla de criterios en el plan)."""
    corte = hoy - relativedelta(months=3)

    candidatos = [
        r for r in registros
        if cumple_filtros_globales(r, aplica_fecha_minima=False, aplica_codigos_excluidos=False)
        and r.fecha_matriculacion is not None
        and r.fecha_servicio is not None
    ]

    deduplicados = deduplicar_por_matricula_ultima_visita(candidatos)

    return [
        r for r in deduplicados
        if r.fecha_matriculacion <= corte
        and r.fecha_servicio <= corte
        and (r.km_ultimo_servicio is None or r.km_ultimo_servicio < KM_MAXIMO_ULTIMO_SERVICIO)
    ]
