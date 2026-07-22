from datetime import date
from io import BytesIO

import openpyxl

from models import CampanaId, RegistroCliente
from excel_writer import generar_excel, nombre_archivo_excel


def test_genera_excel_con_cabeceras_base_y_valores_tipados():
    registro = RegistroCliente(
        matricula="1234ABC", descripcion="NMAX", municipio="Telde",
        fecha_matriculacion=date(2020, 1, 1), fecha_servicio=date(2024, 1, 1),
        km_ultimo_servicio=5000, codigo_servicio="OK1", saludo="Sr.",
        telefono="600123456", email="cliente@example.com",
    )

    excel_bytes = generar_excel([registro], campana=CampanaId.TRES_MESES)

    libro = openpyxl.load_workbook(BytesIO(excel_bytes))
    hoja = libro.active
    cabecera = [celda.value for celda in hoja[1]]
    fila = [celda.value for celda in hoja[2]]

    assert cabecera == [
        "FECHA MATRICULACION", "N MATRICULA", "DESCRIPCION", "FECHA DE SERVICIO",
        "KILOMETRAJE ULTIMO SERVICIO", "CODIGO SERVICIO", "KILOMETRAJE MANTENIMIENTO",
        "FIN MANTENIMIENTO", "SALUDO", "TELEFONO", "EMAIL", "DIRECCION",
    ]
    # El kilometraje se guarda como número (int), no como texto, a diferencia
    # del CSV — Excel puede tener columnas numéricas de verdad.
    assert fila[4] == 5000
    assert isinstance(fila[4], int)
    assert fila[1] == "1234ABC"


def test_campana_16m_incluye_columnas_de_garantia_en_excel():
    registro = RegistroCliente(
        matricula="1234ABC", descripcion="NMAX", municipio="Telde",
        fecha_matriculacion=date(2020, 1, 1),
        fecha_exp_garantia=date(2022, 1, 1),
    )

    excel_bytes = generar_excel([registro], campana=CampanaId.DIECISEIS_MESES_GARANTIA)

    libro = openpyxl.load_workbook(BytesIO(excel_bytes))
    cabecera = [celda.value for celda in libro.active[1]]

    assert "FECHA EXP GARANTIA" in cabecera
    assert "INICIO GARANT EXTEND" in cabecera


def test_nombre_archivo_incluye_campana_fecha_y_extension_xlsx():
    nombre = nombre_archivo_excel(CampanaId.VEINTICUATRO_MESES, hoy=date(2026, 7, 21))
    assert nombre == "FiltradoCampana24M_2026-07-21.xlsx"
