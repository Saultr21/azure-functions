# Flick/SegmentacionCampanas/campanas/campana_16m_garantia.py
from datetime import date

from models import RegistroCliente
from filtros_globales import cumple_filtros_globales
from dedup import deduplicar_por_matricula_ultima_fila
from utils import restar_meses_estilo_js


def filtrar_16m_garantia(registros: list[RegistroCliente], *, hoy: date) -> list[RegistroCliente]:
    """Réplica exacta de '16 m garantía ±30d.osts'. Ventana de matriculación
    de 15 a 16 meses atrás (campaña de venta proactiva de garantía extendida,
    ver spec §1 -- el nombre "16M garantía" NO se refiere a la fecha de
    expiración de garantía, sino a los meses desde la matriculación). Usa
    restar_meses_estilo_js (no relativedelta) -- ver fix de Task 7, el script
    real también usa setMonth() y por tanto tiene el mismo overflow."""
    desde = restar_meses_estilo_js(hoy, 16)
    hasta = restar_meses_estilo_js(hoy, 15)

    candidatos = [
        r for r in registros
        if cumple_filtros_globales(r, aplica_fecha_minima=False)
        and r.fecha_matriculacion is not None
        and desde <= r.fecha_matriculacion < hasta
        and r.inicio_garantia_extendida is None
    ]

    return deduplicar_por_matricula_ultima_fila(candidatos)
