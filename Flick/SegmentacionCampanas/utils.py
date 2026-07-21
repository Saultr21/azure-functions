"""Utilidades de normalización de texto y parseo de fechas.

Replica el comportamiento de `normalize()`, `cleanModelText()` y `parseFecha()`
de los Office Scripts originales (ver `Flick/office-scripts-actuales/`), para
que la migración a Python produzca resultados idénticos byte a byte en las
comparaciones de municipio, modelo de vehículo y fechas de vencimiento.
"""

import re
import unicodedata
from datetime import date, datetime, timedelta
from typing import Optional, Union

_EXCEL_EPOCH = date(1899, 12, 30)  # mismo offset que (v - 25569) * 86400 en los .osts


def normalizar_texto(valor: Optional[str]) -> str:
    """Quita acentos, pasa a minúsculas y recorta espacios. Replica `normalize()`
    de los Office Scripts, usado para comparar municipios."""
    if not valor:
        return ""
    sin_acentos = unicodedata.normalize("NFD", str(valor))
    sin_acentos = "".join(c for c in sin_acentos if unicodedata.category(c) != "Mn")
    return sin_acentos.lower().strip()


def limpiar_texto_modelo(valor: Optional[str]) -> str:
    """Normaliza y además elimina cualquier carácter no alfanumérico. Replica
    `cleanModelText()`, usado para comparar el modelo de vehículo."""
    base = normalizar_texto(valor)
    return re.sub(r"[^a-z0-9]", "", base)


def parsear_fecha(valor: Union[str, int, float, date, datetime, None]) -> Optional[date]:
    """Replica `parseFecha()` de los Office Scripts: soporta fecha ya parseada,
    número de serie de Excel, texto DD/MM/YYYY, y valores nulos ("--/--/--")."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, (int, float)):
        return _EXCEL_EPOCH + timedelta(days=int(valor))

    texto = str(valor).strip()
    if not texto or texto == "--/--/--":
        return None

    partes = texto.split("/")
    if len(partes) == 3:
        try:
            dia, mes, anio = (int(p) for p in partes)
            return date(anio, mes, dia)
        except ValueError:
            return None

    try:
        return datetime.fromisoformat(texto).date()
    except ValueError:
        return None
