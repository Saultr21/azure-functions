from datetime import date

from models import RegistroCliente
from dedup import deduplicar_por_matricula_ultima_visita, deduplicar_por_matricula_ultima_fila


def _registro(matricula: str, fecha_servicio: date) -> RegistroCliente:
    return RegistroCliente(
        matricula=matricula, descripcion="NMAX", municipio="Telde",
        fecha_servicio=fecha_servicio,
    )


def test_conserva_la_visita_mas_reciente_por_matricula():
    registros = [
        _registro("AAA", date(2023, 1, 1)),
        _registro("AAA", date(2024, 6, 1)),
        _registro("BBB", date(2022, 3, 3)),
    ]

    resultado = deduplicar_por_matricula_ultima_visita(registros)

    assert len(resultado) == 2
    aaa = next(r for r in resultado if r.matricula == "AAA")
    assert aaa.fecha_servicio == date(2024, 6, 1)


def test_conserva_la_ultima_fila_leida_por_matricula():
    registros = [
        _registro("AAA", date(2023, 1, 1)),
        _registro("AAA", date(2020, 1, 1)),  # fecha anterior, pero es la última fila
    ]

    resultado = deduplicar_por_matricula_ultima_fila(registros)

    assert len(resultado) == 1
    assert resultado[0].fecha_servicio == date(2020, 1, 1)
