from datetime import date, timedelta

from models import RegistroCliente
from campanas.campana_46m_preitv import filtrar_46m_preitv

HOY = date(2026, 7, 21)


def _registro(**overrides) -> RegistroCliente:
    base = dict(
        matricula="1234ABC", descripcion="Yamaha NMAX 125", municipio="Telde",
        fecha_matriculacion=date(2020, 1, 1),
        fecha_servicio=HOY - timedelta(days=1450),  # > 46 meses atrás
        codigo_servicio="OK1",
    )
    base.update(overrides)
    return RegistroCliente(**base)


def test_incluye_vehiculo_sin_visita_hace_mas_de_46_meses():
    resultado = filtrar_46m_preitv([_registro()], hoy=HOY)
    assert len(resultado) == 1


def test_excluye_visita_reciente():
    resultado = filtrar_46m_preitv([_registro(fecha_servicio=HOY - timedelta(days=200))], hoy=HOY)
    assert resultado == []
