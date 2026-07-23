from datetime import date

from models import RegistroCliente
from filtros_globales import (
    cumple_filtros_globales,
    tiene_codigo_excluido,
    municipios_no_reconocidos,
    resumen_municipios_no_reconocidos,
)

BASE = dict(
    matricula="1234ABC", descripcion="Yamaha NMAX 125", municipio="Telde",
    fecha_matriculacion=date(2020, 1, 1),
    fecha_servicio=date(2024, 1, 1),
    codigo_servicio="OK1",
)


def test_modelo_no_permitido_se_descarta():
    r = RegistroCliente(**{**BASE, "descripcion": "Yamaha R1"})
    assert cumple_filtros_globales(r, aplica_fecha_minima=False) is False


def test_municipio_no_permitido_se_descarta():
    r = RegistroCliente(**{**BASE, "municipio": "Madrid"})
    assert cumple_filtros_globales(r, aplica_fecha_minima=False) is False


def test_registro_valido_sin_filtros_opcionales_se_acepta():
    r = RegistroCliente(**BASE)
    assert cumple_filtros_globales(r, aplica_fecha_minima=False) is True


def test_fecha_minima_2019_descarta_matriculaciones_anteriores():
    r = RegistroCliente(**{**BASE, "fecha_matriculacion": date(2018, 12, 31)})
    assert cumple_filtros_globales(r, aplica_fecha_minima=True) is False


def test_tiene_codigo_excluido_true_para_codigo_en_lista():
    r = RegistroCliente(**{**BASE, "codigo_servicio": "PRE"})
    assert tiene_codigo_excluido(r) is True


def test_tiene_codigo_excluido_false_para_codigo_valido():
    r = RegistroCliente(**{**BASE, "codigo_servicio": "OK1"})
    assert tiene_codigo_excluido(r) is False


def test_municipios_no_reconocidos_cuenta_solo_modelos_yamaha_validos():
    valido_municipio_desconocido = RegistroCliente(**{**BASE, "municipio": "Agaete"})
    valido_municipio_desconocido_repetido = RegistroCliente(**{**BASE, "municipio": "Agaete"})
    modelo_no_yamaha_mismo_municipio = RegistroCliente(
        **{**BASE, "descripcion": "Yamaha R1", "municipio": "Arinaga"}
    )
    municipio_reconocido = RegistroCliente(**{**BASE, "municipio": "Telde"})

    conteo = municipios_no_reconocidos([
        valido_municipio_desconocido,
        valido_municipio_desconocido_repetido,
        modelo_no_yamaha_mismo_municipio,
        municipio_reconocido,
    ])

    # Arinaga no cuenta: el modelo no es un Yamaha válido, así que ese
    # registro ya se habría descartado por modelo, no por municipio.
    assert conteo == {"Agaete": 2}


def test_municipios_no_reconocidos_vacio_cuando_todo_es_valido():
    r = RegistroCliente(**BASE)
    assert municipios_no_reconocidos([r]) == {}


def test_municipios_no_reconocidos_agrupa_municipio_vacio():
    r = RegistroCliente(**{**BASE, "municipio": "  "})
    assert municipios_no_reconocidos([r]) == {"(vacío)": 1}


def test_resumen_vacio_devuelve_cero_y_cadena_vacia():
    assert resumen_municipios_no_reconocidos({}) == (0, "")


def test_resumen_suma_total_y_formatea_detalle():
    total, resumen = resumen_municipios_no_reconocidos({"Agaete": 906, "Mogán": 12})
    assert total == 918
    assert resumen == "Agaete: 906; Mogán: 12"


def test_resumen_agrupa_los_que_superan_el_tope():
    conteo = {f"Municipio{i}": (20 - i) for i in range(12)}  # 12 municipios, ordenados desc
    total, resumen = resumen_municipios_no_reconocidos(conteo, tope=10)
    assert total == sum(conteo.values())
    # Muestra los 10 primeros y agrupa los 2 restantes.
    assert resumen.endswith("; y 2 municipio(s) más")
    assert resumen.count(":") == 10
