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
    real también usa setMonth() y por tanto tiene el mismo overflow.

    Divergencia conocida y aceptada en el filtro de "Inicio.garant.extend"
    (revisión de calidad de código sobre el commit
    9027c8194879065f91cceb1ca9c00296b3785c5a): el script real
    (`16 m garantía ±30d.osts`) compara el texto crudo de la celda:
    `if (inicioExt && inicioExt !== "--/--/--") continue;` -- es decir,
    excluye la fila si el valor es CUALQUIER string no vacío distinto del
    placeholder "--/--/--", incluido texto basura/no parseable como fecha
    (p. ej. un typo). Aquí, en cambio, se comprueba
    `r.inicio_garantia_extendida is None`, y ese valor viene de
    `parsear_fecha()` (ver `utils.py`), que mapea tanto una celda realmente
    vacía como un texto no parseable al mismo `None`. Por tanto, si esa
    columna llegara a contener texto no vacío pero inválido como fecha, el
    script real excluiría la fila y este puerto la incluiría. Se acepta esta
    divergencia sin corregirla ahora porque, en la práctica, esa columna solo
    contiene fechas válidas o el placeholder "--/--/--" en los datos reales;
    cambiar el comportamiento sería una decisión deliberada aparte (y
    obligaría a revisar los 5 tests existentes), no algo a mezclar en un
    fix de documentación."""
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
