"""Generación del CSV de salida con el mismo formato que producen hoy los
Office Scripts: separador punto y coma, cabeceras en español, fechas ISO.
La campaña 16M añade dos columnas de garantía en una posición fija.
Este CSV solo se usa para la vista previa en el chat del agente; el fichero
descargable es el Excel generado por excel_writer.py."""

from models import CampanaId, RegistroCliente

CABECERAS_BASE = [
    "FECHA MATRICULACION", "N MATRICULA", "DESCRIPCION", "FECHA DE SERVICIO",
    "KILOMETRAJE ULTIMO SERVICIO", "CODIGO SERVICIO", "KILOMETRAJE MANTENIMIENTO",
    "FIN MANTENIMIENTO", "SALUDO", "TELEFONO", "EMAIL", "DIRECCION",
]

CABECERAS_GARANTIA_EXTRA = ["FECHA EXP GARANTIA", "INICIO GARANT EXTEND"]

MAPA_CAMPOS = {
    "FECHA MATRICULACION": "fecha_matriculacion",
    "N MATRICULA": "matricula",
    "DESCRIPCION": "descripcion",
    "FECHA DE SERVICIO": "fecha_servicio",
    "KILOMETRAJE ULTIMO SERVICIO": "km_ultimo_servicio",
    "CODIGO SERVICIO": "codigo_servicio",
    "KILOMETRAJE MANTENIMIENTO": "km_mantenimiento",
    "FIN MANTENIMIENTO": "fin_mantenimiento",
    "FECHA EXP GARANTIA": "fecha_exp_garantia",
    "INICIO GARANT EXTEND": "inicio_garantia_extendida",
    "SALUDO": "saludo",
    "TELEFONO": "telefono",
    "EMAIL": "email",
    "DIRECCION": "municipio",
}


def cabeceras_para(campana: CampanaId) -> list[str]:
    """Las cabeceras base valen para las 5 campañas; la 16M inserta las dos
    columnas de garantía justo después de FIN MANTENIMIENTO, igual que el
    Office Script equivalente."""
    if campana == CampanaId.DIECISEIS_MESES_GARANTIA:
        indice_fin_mantenimiento = CABECERAS_BASE.index("FIN MANTENIMIENTO") + 1
        return (
            CABECERAS_BASE[:indice_fin_mantenimiento]
            + CABECERAS_GARANTIA_EXTRA
            + CABECERAS_BASE[indice_fin_mantenimiento:]
        )
    return CABECERAS_BASE


def valor_campo(registro: RegistroCliente, cabecera: str):
    """Lee el campo del registro correspondiente a la cabecera: None si no
    tiene valor, int si es un float entero (Pydantic coerce enteros a float,
    p. ej. 5000 -> 5000.0, y los Office Scripts originales manejan números JS
    puros sin ".0"), o el valor tal cual en el resto de casos."""
    nombre_campo = MAPA_CAMPOS[cabecera]
    valor = getattr(registro, nombre_campo)
    if valor is None:
        return None
    if isinstance(valor, float) and valor.is_integer():
        return int(valor)
    return valor


def _valor_campo_csv(registro: RegistroCliente, cabecera: str) -> str:
    """Versión en texto de valor_campo para el CSV: vacío si es None, y sin
    punto y coma (que rompería el separador) si es texto libre."""
    valor = valor_campo(registro, cabecera)
    texto = "" if valor is None else str(valor)
    return texto.replace(";", ",")


def generar_csv(registros: list[RegistroCliente], *, campana: CampanaId) -> str:
    """Construye el CSV completo (cabecera + filas) en el formato exacto que
    ya usan los Office Scripts, para no romper el flujo de trabajo actual."""
    cabeceras = cabeceras_para(campana)
    lineas = [";".join(cabeceras)]
    for registro in registros:
        lineas.append(";".join(_valor_campo_csv(registro, c) for c in cabeceras))
    return "\n".join(lineas)
