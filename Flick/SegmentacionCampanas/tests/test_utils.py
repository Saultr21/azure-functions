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


def test_parsear_fecha_calendario_invalido_devuelve_none():
    # 31/02 no existe; JS haría rollover a marzo, aquí se descarta el dato.
    assert parsear_fecha("31/02/2020") is None


def test_parsear_fecha_serial_cero_es_ausente():
    # JS usa `!v`, que trata 0 como falsy/ausente; un serial 0 (epoch) nunca
    # es una fecha real de matriculación o servicio.
    assert parsear_fecha(0) is None


def test_parsear_fecha_serie_excel_redondea_imprecision_flotante():
    # 44197 = 2021-01-01 (epoch 1899-12-30). Con float imprecision el serial
    # puede llegar como 44197.0000001 o 44196.9999999; ambos deben redondear
    # al mismo día en vez de truncarse hacia el día anterior.
    assert parsear_fecha(44197.0000001) == date(2021, 1, 1)
    assert parsear_fecha(44196.9999999) == date(2021, 1, 1)


def test_parsear_fecha_fallback_iso_y_formatos_comunes():
    assert parsear_fecha("2021-06-15") == date(2021, 6, 15)
    assert parsear_fecha("15-06-2021") == date(2021, 6, 15)
    assert parsear_fecha("15.06.2021") == date(2021, 6, 15)
