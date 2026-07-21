from datetime import date, timedelta

from models import RegistroCliente
from campanas.campana_3m import filtrar_3m

HOY = date(2026, 7, 21)


def _registro(**overrides) -> RegistroCliente:
    base = dict(
        matricula="1234ABC", descripcion="Yamaha NMAX 125", municipio="Telde",
        fecha_matriculacion=date(2023, 1, 1),
        fecha_servicio=HOY - timedelta(days=200),  # > 3 meses atrás
        km_ultimo_servicio=50,
    )
    base.update(overrides)
    return RegistroCliente(**base)


def test_incluye_vehiculo_sin_visita_hace_mas_de_3_meses_y_km_bajo():
    registros = [_registro()]
    resultado = filtrar_3m(registros, hoy=HOY)
    assert len(resultado) == 1


def test_excluye_por_kilometraje_alto():
    registros = [_registro(km_ultimo_servicio=500)]
    resultado = filtrar_3m(registros, hoy=HOY)
    assert resultado == []


def test_excluye_visita_reciente_menos_de_3_meses():
    registros = [_registro(fecha_servicio=HOY - timedelta(days=10))]
    resultado = filtrar_3m(registros, hoy=HOY)
    assert resultado == []


def test_no_aplica_fecha_minima_2019_ni_codigos_excluidos():
    # Matriculación en 2015 y código PRE: en 3M NO se descartan por esto.
    registros = [_registro(fecha_matriculacion=date(2015, 1, 1), codigo_servicio="PRE")]
    resultado = filtrar_3m(registros, hoy=HOY)
    assert len(resultado) == 1


def test_deduplica_conservando_la_visita_mas_reciente():
    registros = [
        _registro(fecha_servicio=HOY - timedelta(days=400)),
        _registro(fecha_servicio=HOY - timedelta(days=200)),
    ]
    resultado = filtrar_3m(registros, hoy=HOY)
    assert len(resultado) == 1
    assert resultado[0].fecha_servicio == HOY - timedelta(days=200)


def test_cutoff_estilo_js_en_frontera_de_fin_de_mes():
    # hoy=31/05/2026: febrero de 2026 tiene 28 días, así que el cutoff
    # correcto (estilo JS Date.setMonth, con overflow) es 03/03/2026, NO el
    # 28/02/2026 que produciría dateutil.relativedelta (clamp). Este test
    # fija ese comportamiento exacto de frontera para evitar una regresión
    # al bug original.
    hoy_frontera = date(2026, 5, 31)
    fecha_matriculacion_antigua = date(2020, 1, 1)

    registros = [
        _registro(
            fecha_matriculacion=fecha_matriculacion_antigua,
            fecha_servicio=date(2026, 3, 3),  # exactamente en el cutoff -> incluido
        ),
        _registro(
            matricula="9999XYZ",
            fecha_matriculacion=fecha_matriculacion_antigua,
            fecha_servicio=date(2026, 3, 4),  # un día después del cutoff -> excluido
        ),
    ]

    resultado = filtrar_3m(registros, hoy=hoy_frontera)

    matriculas_incluidas = {r.matricula for r in resultado}
    assert matriculas_incluidas == {"1234ABC"}
