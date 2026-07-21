from datetime import date

from models import RegistroCliente
from filtros_globales import cumple_filtros_globales

BASE = dict(
    matricula="1234ABC", descripcion="Yamaha NMAX 125", municipio="Telde",
    fecha_matriculacion=date(2020, 1, 1),
    fecha_servicio=date(2024, 1, 1),
    codigo_servicio="OK1",
)


def test_modelo_no_permitido_se_descarta():
    r = RegistroCliente(**{**BASE, "descripcion": "Yamaha R1"})
    assert cumple_filtros_globales(r, aplica_fecha_minima=False, aplica_codigos_excluidos=False) is False


def test_municipio_no_permitido_se_descarta():
    r = RegistroCliente(**{**BASE, "municipio": "Madrid"})
    assert cumple_filtros_globales(r, aplica_fecha_minima=False, aplica_codigos_excluidos=False) is False


def test_registro_valido_sin_filtros_opcionales_se_acepta():
    r = RegistroCliente(**BASE)
    assert cumple_filtros_globales(r, aplica_fecha_minima=False, aplica_codigos_excluidos=False) is True


def test_fecha_minima_2019_descarta_matriculaciones_anteriores():
    r = RegistroCliente(**{**BASE, "fecha_matriculacion": date(2018, 12, 31)})
    assert cumple_filtros_globales(r, aplica_fecha_minima=True, aplica_codigos_excluidos=False) is False


def test_codigo_excluido_descarta_el_registro():
    r = RegistroCliente(**{**BASE, "codigo_servicio": "PRE"})
    assert cumple_filtros_globales(r, aplica_fecha_minima=False, aplica_codigos_excluidos=True) is False


def test_codigo_excluido_no_aplica_si_esta_desactivado():
    r = RegistroCliente(**{**BASE, "codigo_servicio": "PRE"})
    assert cumple_filtros_globales(r, aplica_fecha_minima=False, aplica_codigos_excluidos=False) is True
