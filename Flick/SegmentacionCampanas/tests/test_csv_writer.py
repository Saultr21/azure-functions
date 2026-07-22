from datetime import date

from models import CampanaId, RegistroCliente
from csv_writer import generar_csv


def test_genera_csv_con_separador_punto_y_coma_y_cabeceras_base():
    registro = RegistroCliente(
        matricula="1234ABC", descripcion="NMAX", municipio="Telde",
        fecha_matriculacion=date(2020, 1, 1), fecha_servicio=date(2024, 1, 1),
        km_ultimo_servicio=5000, codigo_servicio="OK1", saludo="Sr.",
        telefono="600123456", email="cliente@example.com",
    )

    csv_texto = generar_csv([registro], campana=CampanaId.TRES_MESES)

    lineas = csv_texto.strip().split("\n")
    assert lineas[0] == (
        "FECHA MATRICULACION;N MATRICULA;DESCRIPCION;FECHA DE SERVICIO;"
        "KILOMETRAJE ULTIMO SERVICIO;CODIGO SERVICIO;KILOMETRAJE MANTENIMIENTO;"
        "FIN MANTENIMIENTO;SALUDO;TELEFONO;EMAIL;DIRECCION"
    )
    assert lineas[1] == (
        "2020-01-01;1234ABC;NMAX;2024-01-01;5000;OK1;;;Sr.;600123456;"
        "cliente@example.com;Telde"
    )


def test_km_fraccionario_se_muestra_sin_ceros_de_relleno():
    registro = RegistroCliente(
        matricula="1234ABC", descripcion="NMAX", municipio="Telde",
        fecha_matriculacion=date(2020, 1, 1), fecha_servicio=date(2024, 1, 1),
        km_ultimo_servicio=1234.5, codigo_servicio="OK1", saludo="Sr.",
        telefono="600123456", email="cliente@example.com",
    )

    csv_texto = generar_csv([registro], campana=CampanaId.TRES_MESES)

    lineas = csv_texto.strip().split("\n")
    assert lineas[1] == (
        "2020-01-01;1234ABC;NMAX;2024-01-01;1234.5;OK1;;;Sr.;600123456;"
        "cliente@example.com;Telde"
    )


def test_campana_16m_incluye_columnas_de_garantia():
    registro = RegistroCliente(
        matricula="1234ABC", descripcion="NMAX", municipio="Telde",
        fecha_matriculacion=date(2020, 1, 1),
        fecha_exp_garantia=date(2022, 1, 1),
    )

    csv_texto = generar_csv([registro], campana=CampanaId.DIECISEIS_MESES_GARANTIA)

    assert "FECHA EXP GARANTIA" in csv_texto.split("\n")[0]
    assert "INICIO GARANT EXTEND" in csv_texto.split("\n")[0]
