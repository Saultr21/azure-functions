from datetime import date, timedelta

from models import RegistroCliente
from campanas.campana_24m import filtrar_24m

HOY = date(2026, 7, 21)


def _registro(**overrides) -> RegistroCliente:
    base = dict(
        matricula="1234ABC", descripcion="Yamaha NMAX 125", municipio="Telde",
        fecha_matriculacion=date(2020, 1, 1),
        fecha_servicio=HOY - timedelta(days=800),  # > 24 meses atrás
        codigo_servicio="OK1",
    )
    base.update(overrides)
    return RegistroCliente(**base)


def test_incluye_vehiculo_sin_visita_hace_mas_de_24_meses():
    resultado = filtrar_24m([_registro()], hoy=HOY)
    assert len(resultado) == 1


def test_excluye_visita_reciente():
    resultado = filtrar_24m([_registro(fecha_servicio=HOY - timedelta(days=30))], hoy=HOY)
    assert resultado == []


def test_excluye_matriculacion_anterior_a_2019():
    resultado = filtrar_24m([_registro(fecha_matriculacion=date(2018, 12, 31))], hoy=HOY)
    assert resultado == []


def test_excluye_codigo_servicio_excluido():
    resultado = filtrar_24m([_registro(codigo_servicio="YGR")], hoy=HOY)
    assert resultado == []


def test_ordena_por_fecha_de_servicio_ascendente():
    registros = [
        _registro(matricula="AAA", fecha_servicio=HOY - timedelta(days=900)),
        _registro(matricula="BBB", fecha_servicio=HOY - timedelta(days=1200)),
    ]
    resultado = filtrar_24m(registros, hoy=HOY)
    assert [r.matricula for r in resultado] == ["BBB", "AAA"]
