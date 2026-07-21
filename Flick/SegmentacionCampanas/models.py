from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_validator


class CampanaId(str, Enum):
    TRES_MESES = "3M"
    VEINTICUATRO_MESES = "24M"
    TREINTAYSEIS_MESES = "36M"
    CUARENTAYSEIS_MESES_PREITV = "46M"
    DIECISEIS_MESES_GARANTIA = "16M"


class RegistroCliente(BaseModel):
    """Una fila normalizada del Excel maestro, ya con los campos que interesan
    a cualquier campaña. Los campos específicos de garantía son opcionales
    porque solo los usa la campaña 16M."""

    matricula: str
    descripcion: str
    municipio: str
    fecha_matriculacion: Optional[date] = None
    fecha_servicio: Optional[date] = None
    km_ultimo_servicio: Optional[float] = None
    km_mantenimiento: Optional[float] = None
    codigo_servicio: str = ""
    fin_mantenimiento: Optional[date] = None
    fecha_exp_garantia: Optional[date] = None
    inicio_garantia_extendida: Optional[date] = None
    saludo: str = ""
    telefono: str = ""
    email: str = ""

    @field_validator("matricula")
    @classmethod
    def matricula_no_vacia(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("matricula no puede estar vacía")
        return v.strip()


class ErrorResponse(BaseModel):
    codigo: str
    mensaje: str
