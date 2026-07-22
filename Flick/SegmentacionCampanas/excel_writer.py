"""Generación del Excel (.xlsx) de salida, con las mismas cabeceras y datos
que el CSV histórico. Es el fichero que se ofrece para descarga; el CSV sigue
existiendo aparte para la vista previa en el chat del agente."""

from datetime import date
from io import BytesIO

import openpyxl

from csv_writer import cabeceras_para, valor_campo
from models import CampanaId, RegistroCliente


def generar_excel(registros: list[RegistroCliente], *, campana: CampanaId) -> bytes:
    """Construye el .xlsx completo (cabecera + filas) y lo devuelve como
    bytes, listo para subir a Blob Storage."""
    cabeceras = cabeceras_para(campana)

    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.title = "Candidatos"
    hoja.append(cabeceras)
    for registro in registros:
        hoja.append([valor_campo(registro, c) for c in cabeceras])

    buffer = BytesIO()
    libro.save(buffer)
    return buffer.getvalue()


def nombre_archivo_excel(campana: CampanaId, *, hoy: date) -> str:
    """Nombre del fichero de salida: FiltradoCampana<ID>_<fecha ISO>.xlsx."""
    return f"FiltradoCampana{campana.value}_{hoy.isoformat()}.xlsx"
