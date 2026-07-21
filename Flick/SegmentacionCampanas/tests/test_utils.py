from datetime import date

from utils import normalizar_texto, limpiar_texto_modelo, parsear_fecha


def test_normalizar_texto_quita_acentos_y_minusculas():
    assert normalizar_texto("Gáldar") == "galdar"
    assert normalizar_texto("  Santa Brígida  ") == "santa brigida"
    assert normalizar_texto(None) == ""


def test_limpiar_texto_modelo_quita_todo_lo_no_alfanumerico():
    assert limpiar_texto_modelo("YAMAHA NMAX 125 (2021)") == "yamahanmax1252021"
    assert limpiar_texto_modelo("Tenere-700") == "tenere700"


def test_parsear_fecha_formato_dd_mm_yyyy():
    assert parsear_fecha("01/02/2020") == date(2020, 2, 1)


def test_parsear_fecha_valor_nulo():
    assert parsear_fecha("--/--/--") is None
    assert parsear_fecha(None) is None
    assert parsear_fecha("") is None


def test_parsear_fecha_serie_excel():
    # 25569 = 1970-01-01 en el sistema de fechas de Excel (base 1900);
    # 44197 = 2021-01-01 con el mismo epoch (1899-12-30)
    assert parsear_fecha(44197) == date(2021, 1, 1)


def test_parsear_fecha_ya_es_date():
    assert parsear_fecha(date(2022, 5, 10)) == date(2022, 5, 10)
