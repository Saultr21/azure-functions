# Flick/SegmentacionCampanas/campanas/motor.py
from dataclasses import dataclass
from datetime import date

from models import CampanaId
from excel_reader import leer_registros
from csv_writer import generar_csv
from excel_writer import generar_excel, nombre_archivo_excel

from campanas.campana_3m import filtrar_3m
from campanas.campana_24m import filtrar_24m
from campanas.campana_36m import filtrar_36m
from campanas.campana_46m_preitv import filtrar_46m_preitv
from campanas.campana_16m_garantia import filtrar_16m_garantia


class CampanaNoSoportadaError(Exception):
    pass


@dataclass
class ResultadoCampana:
    total_clientes: int
    csv_contenido: str
    excel_contenido: bytes
    nombre_archivo: str


_FILTROS_POR_CAMPANA = {
    CampanaId.TRES_MESES: filtrar_3m,
    CampanaId.VEINTICUATRO_MESES: filtrar_24m,
    CampanaId.TREINTAYSEIS_MESES: filtrar_36m,
    CampanaId.CUARENTAYSEIS_MESES_PREITV: filtrar_46m_preitv,
    CampanaId.DIECISEIS_MESES_GARANTIA: filtrar_16m_garantia,
}


def ejecutar_campana(campana_id: str, excel_bytes: bytes, *, hoy: date) -> ResultadoCampana:
    try:
        campana = CampanaId(campana_id)
    except ValueError as exc:
        raise CampanaNoSoportadaError(f"Campaña desconocida: '{campana_id}'") from exc

    registros = leer_registros(excel_bytes)
    filtro = _FILTROS_POR_CAMPANA[campana]
    resultado = filtro(registros, hoy=hoy)

    csv_contenido = generar_csv(resultado, campana=campana)
    excel_contenido = generar_excel(resultado, campana=campana)
    nombre_archivo = nombre_archivo_excel(campana, hoy=hoy)

    return ResultadoCampana(
        total_clientes=len(resultado),
        csv_contenido=csv_contenido,
        excel_contenido=excel_contenido,
        nombre_archivo=nombre_archivo,
    )
