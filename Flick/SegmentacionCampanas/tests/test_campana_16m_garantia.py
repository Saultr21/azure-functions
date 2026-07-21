from datetime import date, timedelta

from models import RegistroCliente
from campanas.campana_16m_garantia import filtrar_16m_garantia

HOY = date(2026, 7, 21)


def _registro(**overrides) -> RegistroCliente:
    base = dict(
        matricula="1234ABC", descripcion="Yamaha NMAX 125", municipio="Telde",
        fecha_matriculacion=HOY - timedelta(days=460),  # ~15.1 meses atrás
        inicio_garantia_extendida=None,
    )
    base.update(overrides)
    return RegistroCliente(**base)


def test_incluye_matriculacion_en_ventana_15_16_meses_sin_garantia_extendida():
    resultado = filtrar_16m_garantia([_registro()], hoy=HOY)
    assert len(resultado) == 1


def test_excluye_si_ya_tiene_garantia_extendida_iniciada():
    resultado = filtrar_16m_garantia(
        [_registro(inicio_garantia_extendida=date(2025, 1, 1))], hoy=HOY
    )
    assert resultado == []


def test_excluye_matriculacion_fuera_de_ventana_muy_reciente():
    resultado = filtrar_16m_garantia(
        [_registro(fecha_matriculacion=HOY - timedelta(days=60))], hoy=HOY
    )
    assert resultado == []


def test_excluye_matriculacion_fuera_de_ventana_muy_antigua():
    resultado = filtrar_16m_garantia(
        [_registro(fecha_matriculacion=HOY - timedelta(days=900))], hoy=HOY
    )
    assert resultado == []


def test_deduplica_quedandose_con_la_ultima_fila_leida():
    registros = [
        _registro(matricula="AAA", fecha_matriculacion=HOY - timedelta(days=455)),
        _registro(matricula="AAA", fecha_matriculacion=HOY - timedelta(days=465)),
    ]
    resultado = filtrar_16m_garantia(registros, hoy=HOY)
    assert len(resultado) == 1
    assert resultado[0].fecha_matriculacion == HOY - timedelta(days=465)
