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
    número de serie de Excel, texto DD/MM/YYYY, y valores nulos ("--/--/--").

    Divergencias deliberadas frente al JS original (ver revisión de calidad de
    código sobre el commit e64dd43):

    - Fechas de calendario inválidas (p. ej. 31/02/2020): JS `new Date(y, m-1, d)`
      hace "rollover" silencioso (31/02/2020 -> 02/03/2020). Aquí se prefiere
      devolver `None`, porque descartar un dato con una fecha mal tecleada es
      más seguro que reasignarlo silenciosamente a otra fecha real.
    - Solo 1 de los 5 scripts (`16 m garantía ±30d.osts`) prueba ISO/`Date.parse`
      ANTES de partir por "/"; los otros 4 (incluido `Fecha24MesesSinVisita(CSV).osts`)
      parten primero por "/" y solo caen a `new Date(s)` (parser JS laxo) si eso
      falla. Como 4 de las 5 campañas que usa esta función siguen el patrón
      mayoritario, se mantiene aquí el orden DD/MM/YYYY-primero como default.
    """
    # JS usa `!v`, que trata 0 como "ausente". Un serial de Excel igual a 0
    # (equivalente a 1899-12-30, el epoch) nunca es una fecha de matriculación
    # o servicio real, así que se trata como ausente igual que en el original.
    if valor is None or valor == "" or valor == 0:
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, (int, float)):
        # round() en lugar de int(): un serial de Excel puede llegar con
        # imprecisión de punto flotante (p. ej. 44197.0000001 o 44196.9999999
        # en vez de 44197 exacto); truncar con int() podría desplazar la
        # fecha resultante un día en el peor caso.
        return _EXCEL_EPOCH + timedelta(days=round(valor))

    texto = str(valor).strip()
    if not texto or texto == "--/--/--":
        return None

    partes = texto.split("/")
    if len(partes) == 3:
        try:
            dia, mes, anio = (int(p) for p in partes)
            return date(anio, mes, dia)
        except ValueError:
            # Cubre tanto partes no numéricas como fechas de calendario
            # inválidas (ValueError de `date()`, p. ej. 31/02/2020): se
            # devuelve None en vez de replicar el rollover de JS.
            return None

    # Fallback para textos que no son DD/MM/YYYY. Réplica "best effort" del
    # parser laxo `new Date(s)` de JS -- no es un match perfecto, pero cubre
    # los formatos plausibles en esta exportación de Excel usando solo la
    # librería estándar (sin nuevas dependencias).
    try:
        return datetime.fromisoformat(texto).date()
    except ValueError:
        pass

    for formato in ("%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue

    return None
