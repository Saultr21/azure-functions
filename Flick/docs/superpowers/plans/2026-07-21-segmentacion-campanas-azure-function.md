# Motor de Segmentación de Campañas (Azure Function) — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir `Flick/SegmentacionCampanas/`, una Azure Function en Python que sustituye a los 5 Office Scripts actuales, replicando exactamente el comportamiento verificado en producción para las campañas 3M, 24M y 16M-garantía, e implementando 36M y 46M/Pre-ITV a partir de la descripción del PDF (pendientes de validación manual).

**Architecture:** HTTP trigger (`function_app.py`) recibe el Excel maestro como binario crudo + el id de campaña por query string, delega en un motor de filtrado config-driven (`campaigns.py` + `filters.py`), genera un CSV y lo sube a Blob Storage devolviendo una URL SAS de 24h. Ver spec: `Flick/docs/superpowers/specs/2026-07-21-motor-segmentacion-azure-function-design.md`.

**Tech Stack:** Python 3.10, Azure Functions Python v4 (`azure-functions`), `openpyxl` (lectura Excel), `pydantic` v2 (validación), `azure-storage-blob` (subida CSV + SAS), `pytest` (tests).

---

## Referencia — criterios exactos verificados por campaña

Esta tabla es la fuente de verdad para las Tasks 7-10. Viene de leer los `.osts` reales en
`Flick/office-scripts-actuales/`, no del PDF (ver spec §1 para las discrepancias encontradas).

| Campaña | Filtro modelo/municipio | Fecha mínima matriculación (2019) | Códigos excluidos (PRE/YGR/YIT) | Criterio específico | Dedup + orden |
|---|---|---|---|---|---|
| 3M | Sí | **No** | **No** | `fecha_matriculacion > corte_3m` → excluir; `fecha_servicio > corte_3m` → excluir; `km_ultimo_servicio >= 200` → excluir | Dedup por matrícula (última visita). Sin ordenar. |
| 24M | Sí | Sí | Sí | `fecha_servicio > corte_24m` → excluir | Dedup por matrícula (última visita). Orden ascendente por fecha de servicio. |
| 16M garantía | Sí | No (ventana ya es reciente) | No | `fecha_matriculacion` dentro de `[hoy-16m, hoy-15m)` **Y** `inicio_garantia_extendida` vacío | Dedup por matrícula (se queda la última fila leída, sin comparar fechas). |
| 36M *(sin script real — PDF)* | Sí | Sí (asumido) | Sí (asumido) | `fecha_servicio > corte_36m` → excluir | Dedup por matrícula (última visita). Orden ascendente por fecha de servicio. |
| 46M/Pre-ITV *(sin script real — PDF)* | Sí | Sí (asumido) | Sí (asumido) | `fecha_servicio > corte_46m` → excluir | Dedup por matrícula (última visita). Orden ascendente por fecha de servicio. |

`corte_XM` = fecha de hoy menos X meses.

---

### Task 1: Scaffolding del proyecto

**Files:**
- Create: `Flick/SegmentacionCampanas/host.json`
- Create: `Flick/SegmentacionCampanas/requirements.txt`
- Create: `Flick/SegmentacionCampanas/function_app.py`
- Create: `Flick/SegmentacionCampanas/.funcignore`
- Create: `Flick/SegmentacionCampanas/local.settings.json.example`
- Create: `Flick/SegmentacionCampanas/tests/__init__.py`

- [ ] **Step 1: Crear `host.json`**

```json
{
  "version": "2.0",
  "logging": {
    "applicationInsights": {
      "samplingSettings": {
        "isEnabled": true,
        "excludedTypes": "Request"
      }
    }
  },
  "extensionBundle": {
    "id": "Microsoft.Azure.Functions.ExtensionBundle",
    "version": "[4.*, 5.0.0)"
  }
}
```

- [ ] **Step 2: Crear `requirements.txt`**

```
azure-functions
openpyxl>=3.1,<4.0
pydantic>=2.6,<3.0
azure-storage-blob>=12.19,<13.0
```

- [ ] **Step 3: Crear `.funcignore`**

```
tests/
.venv/
__pycache__/
*.pyc
local.settings.json
```

- [ ] **Step 4: Crear `local.settings.json.example`** (nunca commitear `local.settings.json` real — ya está en `.gitignore` de la raíz)

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "BLOB_CONNECTION_STRING": "<connection-string-del-storage-account>",
    "BLOB_CONTAINER_NAME": "csv-campanas"
  }
}
```

- [ ] **Step 5: Crear `function_app.py` esqueleto** (se completa en Task 12)

```python
import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.route(route="segmentar_campana", methods=["POST"])
def segmentar_campana(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse("not implemented", status_code=501)
```

- [ ] **Step 6: Crear `tests/__init__.py` vacío**

- [ ] **Step 7: Commit**

```bash
git add Flick/SegmentacionCampanas/host.json Flick/SegmentacionCampanas/requirements.txt Flick/SegmentacionCampanas/function_app.py Flick/SegmentacionCampanas/.funcignore Flick/SegmentacionCampanas/local.settings.json.example Flick/SegmentacionCampanas/tests/__init__.py
git commit -m "feat(segmentacion): scaffolding inicial de la Azure Function"
```

---

### Task 2: Modelos (Pydantic)

**Files:**
- Create: `Flick/SegmentacionCampanas/models.py`
- Test: `Flick/SegmentacionCampanas/tests/test_models.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# Flick/SegmentacionCampanas/tests/test_models.py
import pytest
from pydantic import ValidationError

from models import CampanaId, RegistroCliente


def test_campana_id_acepta_solo_valores_conocidos():
    assert CampanaId("3M") == CampanaId.TRES_MESES
    with pytest.raises(ValueError):
        CampanaId("no-existe")


def test_registro_cliente_requiere_matricula():
    with pytest.raises(ValidationError):
        RegistroCliente(matricula="", descripcion="NMAX", municipio="telde")
```

- [ ] **Step 2: Ejecutar y comprobar que falla**

Run: `pytest Flick/SegmentacionCampanas/tests/test_models.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'models'`

- [ ] **Step 3: Implementar `models.py`**

```python
# Flick/SegmentacionCampanas/models.py
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
```

- [ ] **Step 4: Ejecutar y comprobar que pasa**

Run: `pytest Flick/SegmentacionCampanas/tests/test_models.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add Flick/SegmentacionCampanas/models.py Flick/SegmentacionCampanas/tests/test_models.py
git commit -m "feat(segmentacion): modelos Pydantic (CampanaId, RegistroCliente)"
```

---

### Task 3: Utilidades de texto y fecha

**Files:**
- Create: `Flick/SegmentacionCampanas/utils.py`
- Test: `Flick/SegmentacionCampanas/tests/test_utils.py`

Replica exacta de `normalize`, `cleanModelText` y `parseFecha` de los `.osts` reales.

- [ ] **Step 1: Escribir el test que falla**

```python
# Flick/SegmentacionCampanas/tests/test_utils.py
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
    # 25569 = 1970-01-01 en el sistema de fechas de Excel (base 1900)
    # 44197 = 2021-01-01 (verificado con date(1899,12,30) + timedelta(days=44197))
    assert parsear_fecha(44197) == date(2021, 1, 1)


def test_parsear_fecha_ya_es_date():
    assert parsear_fecha(date(2022, 5, 10)) == date(2022, 5, 10)
```

- [ ] **Step 2: Ejecutar y comprobar que falla**

Run: `pytest Flick/SegmentacionCampanas/tests/test_utils.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'utils'`

- [ ] **Step 3: Implementar `utils.py`**

```python
# Flick/SegmentacionCampanas/utils.py
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
```

- [ ] **Step 4: Ejecutar y comprobar que pasa**

Run: `pytest Flick/SegmentacionCampanas/tests/test_utils.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add Flick/SegmentacionCampanas/utils.py Flick/SegmentacionCampanas/tests/test_utils.py
git commit -m "feat(segmentacion): utilidades de normalización de texto y parseo de fechas"
```

---

### Task 4: Filtros globales (modelo, municipio, fecha mínima, códigos excluidos)

> **Nota post-Task 8:** la revisión de código de la campaña 24M encontró que el
> `.osts` real aplica el filtro de códigos excluidos DESPUÉS de deduplicar (no
> a la vez que modelo/municipio/fecha mínima, que sí son pre-dedup). El diseño
> de abajo ya refleja esa corrección: `cumple_filtros_globales` solo cubre los
> tres chequeos pre-dedup; `tiene_codigo_excluido` es una función aparte que
> cada campaña aplica DESPUÉS de deduplicar (ver Task 8).

**Files:**
- Create: `Flick/SegmentacionCampanas/filtros_globales.py`
- Test: `Flick/SegmentacionCampanas/tests/test_filtros_globales.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# Flick/SegmentacionCampanas/tests/test_filtros_globales.py
from datetime import date

from models import RegistroCliente
from filtros_globales import cumple_filtros_globales, tiene_codigo_excluido

BASE = dict(
    matricula="1234ABC",
    descripcion="Yamaha NMAX 125",
    municipio="Telde",
    fecha_matriculacion=date(2020, 1, 1),
    fecha_servicio=date(2024, 1, 1),
    codigo_servicio="OK1",
)


def test_modelo_no_permitido_se_descarta():
    r = RegistroCliente(**{**BASE, "descripcion": "Yamaha R1"})
    assert cumple_filtros_globales(r, aplica_fecha_minima=False) is False


def test_municipio_no_permitido_se_descarta():
    r = RegistroCliente(**{**BASE, "municipio": "Madrid"})
    assert cumple_filtros_globales(r, aplica_fecha_minima=False) is False


def test_registro_valido_sin_filtros_opcionales_se_acepta():
    r = RegistroCliente(**BASE)
    assert cumple_filtros_globales(r, aplica_fecha_minima=False) is True


def test_fecha_minima_2019_descarta_matriculaciones_anteriores():
    r = RegistroCliente(**{**BASE, "fecha_matriculacion": date(2018, 12, 31)})
    assert cumple_filtros_globales(r, aplica_fecha_minima=True) is False


def test_tiene_codigo_excluido_true_para_codigo_en_lista():
    r = RegistroCliente(**{**BASE, "codigo_servicio": "PRE"})
    assert tiene_codigo_excluido(r) is True


def test_tiene_codigo_excluido_false_para_codigo_valido():
    r = RegistroCliente(**BASE)
    assert tiene_codigo_excluido(r) is False
```

- [ ] **Step 2: Ejecutar y comprobar que falla**

Run: `pytest Flick/SegmentacionCampanas/tests/test_filtros_globales.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'filtros_globales'`

- [ ] **Step 3: Implementar `filtros_globales.py`**

```python
# Flick/SegmentacionCampanas/filtros_globales.py
from datetime import date

from models import RegistroCliente
from utils import limpiar_texto_modelo, normalizar_texto

MODELOS_VALIDOS = [
    "nmax", "xmax125", "xmax300", "tmax", "mt125", "mt07", "mt09", "tenere700",
]

MUNICIPIOS_VALIDOS = [
    "arucas", "firgas", "galdar", "ingenio", "moya", "las palmas",
    "santa brigida", "guia", "telde", "teror", "valleseco",
    "valsequillo", "vega de san mateo",
]

CODIGOS_SERVICIO_EXCLUIDOS = {"PRE", "YGR", "YIT"}

FECHA_MINIMA_MATRICULACION = date(2019, 1, 1)


def cumple_filtros_globales(
    registro: RegistroCliente,
    *,
    aplica_fecha_minima: bool,
) -> bool:
    """Chequeos PRE-dedup: modelo y municipio SIEMPRE se comprueban (así lo
    hacen los 5 scripts). Fecha mínima es opcional por campaña — 3M y 16M NO
    la aplican en producción. El filtro de códigos excluidos NO vive aquí:
    ver `tiene_codigo_excluido`, que se aplica DESPUÉS de deduplicar."""
    modelo_limpio = limpiar_texto_modelo(registro.descripcion)
    if not any(m in modelo_limpio for m in MODELOS_VALIDOS):
        return False

    municipio_norm = normalizar_texto(registro.municipio)
    if not any(m in municipio_norm for m in MUNICIPIOS_VALIDOS):
        return False

    if aplica_fecha_minima:
        if registro.fecha_matriculacion is None:
            return False
        if registro.fecha_matriculacion < FECHA_MINIMA_MATRICULACION:
            return False

    return True


def tiene_codigo_excluido(registro: RegistroCliente) -> bool:
    """Chequeo POST-dedup (24M, 36M, 46M): en el script real, el código de
    servicio excluido se comprueba sobre la fila ya deduplicada (la visita
    más reciente), no antes. Aplicarlo pre-dedup permitía que una matrícula
    cuya visita más reciente tiene un código excluido cayera de vuelta a una
    visita anterior válida — bug real encontrado en la revisión de Task 8."""
    return registro.codigo_servicio.strip().upper() in CODIGOS_SERVICIO_EXCLUIDOS
```

- [ ] **Step 4: Ejecutar y comprobar que pasa**

Run: `pytest Flick/SegmentacionCampanas/tests/test_filtros_globales.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add Flick/SegmentacionCampanas/filtros_globales.py Flick/SegmentacionCampanas/tests/test_filtros_globales.py
git commit -m "feat(segmentacion): filtros globales parametrizables por campaña"
```

---

### Task 5: Lector de Excel

**Files:**
- Create: `Flick/SegmentacionCampanas/excel_reader.py`
- Test: `Flick/SegmentacionCampanas/tests/test_excel_reader.py`

El Excel real tiene cabeceras como `Nº.matrícula`, `Fecha.matriculación`, etc. Localizamos
columnas por coincidencia normalizada (igual que `col()` en los `.osts`), no por posición fija.

- [ ] **Step 1: Escribir el test que falla**

```python
# Flick/SegmentacionCampanas/tests/test_excel_reader.py
import io
from datetime import date

import openpyxl
import pytest

from excel_reader import leer_registros, ColumnaFaltanteError

COLUMNAS = [
    "Nº.matrícula", "Descripción", "Direccion(3)", "Fecha.matriculación",
    "Fecha.de.servicio", "Kilometraje", "Kilometraje.mantenim",
    "Código.de.servicio(1)", "Fin.mantenimiento", "Fecha.exp.garantia",
    "Inicio.garant.extend", "Saludo.(tratamiento)", "Nº.telefono(4)",
    "Direccion.e-mail",
]


def _crear_excel_bytes(filas: list[list]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Hoja1"
    ws.append(COLUMNAS)
    for fila in filas:
        ws.append(fila)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def test_lee_una_fila_correctamente():
    fila = [
        "1234ABC", "Yamaha NMAX 125", "Telde", date(2020, 1, 1),
        date(2024, 1, 1), 5000, 10000, "OK1", "--/--/--", "--/--/--",
        "--/--/--", "Sr.", "600123456", "cliente@example.com",
    ]
    excel_bytes = _crear_excel_bytes([fila])

    registros = leer_registros(excel_bytes)

    assert len(registros) == 1
    assert registros[0].matricula == "1234ABC"
    assert registros[0].fecha_matriculacion == date(2020, 1, 1)
    assert registros[0].km_ultimo_servicio == 5000


def test_fila_sin_matricula_se_descarta():
    fila = ["", "Yamaha NMAX 125", "Telde", date(2020, 1, 1), date(2024, 1, 1),
            5000, 10000, "OK1", "--/--/--", "--/--/--", "--/--/--", "Sr.",
            "600123456", "cliente@example.com"]
    excel_bytes = _crear_excel_bytes([fila])

    registros = leer_registros(excel_bytes)

    assert registros == []


def test_falta_una_columna_obligatoria_lanza_error():
    wb_bytes_sin_matricula = _crear_excel_bytes([])
    # Reescribimos quitando la cabecera de matrícula
    wb = openpyxl.load_workbook(io.BytesIO(wb_bytes_sin_matricula))
    ws = wb["Hoja1"]
    ws.cell(row=1, column=1).value = "OtraColumna"
    buffer = io.BytesIO()
    wb.save(buffer)

    with pytest.raises(ColumnaFaltanteError):
        leer_registros(buffer.getvalue())
```

- [ ] **Step 2: Ejecutar y comprobar que falla**

Run: `pytest Flick/SegmentacionCampanas/tests/test_excel_reader.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'excel_reader'`

- [ ] **Step 3: Implementar `excel_reader.py`**

```python
# Flick/SegmentacionCampanas/excel_reader.py
import io
from typing import Optional

import openpyxl

from models import RegistroCliente
from utils import normalizar_texto, parsear_fecha

HOJA_ESPERADA = "Hoja1"

# nombre_campo -> fragmento de cabecera a buscar (normalizado, "contains")
COLUMNAS_REQUERIDAS = {
    "matricula": "matricula",
    "descripcion": "descripcion",
    "municipio": "direccion(3)",
    "fecha_matriculacion": "fecha.matriculacion",
    "fecha_servicio": "fecha.de.servicio",
    "codigo_servicio": "codigo.de.servicio",
    "fin_mantenimiento": "fin.mantenimiento",
    "km_mantenimiento": "kilometraje.mantenim",
    "fecha_exp_garantia": "fecha.exp.garantia",
    "inicio_garantia_extendida": "inicio.garant.extend",
    "saludo": "saludo",
    "telefono": "telefono",
    "email": "e-mail",
}
# Excepción: "Kilometraje" (a secas) hay que matchearlo por igualdad exacta,
# porque "contains" también encontraría "Kilometraje.mantenim" (igual que en
# los .osts, que usan colExact para esta columna).
COLUMNA_KM_ULTIMO_SERVICIO = "kilometraje"


class ColumnaFaltanteError(Exception):
    pass


def _construir_indice_columnas(cabeceras: list[str]) -> dict[str, int]:
    cabeceras_norm = [normalizar_texto(h) for h in cabeceras]
    indice: dict[str, int] = {}

    for campo, fragmento in COLUMNAS_REQUERIDAS.items():
        encontrada = next(
            (i for i, h in enumerate(cabeceras_norm) if fragmento in h), None
        )
        if encontrada is None:
            raise ColumnaFaltanteError(f"No se encontró la columna para '{campo}' ({fragmento})")
        indice[campo] = encontrada

    idx_km = next((i for i, h in enumerate(cabeceras_norm) if h == COLUMNA_KM_ULTIMO_SERVICIO), None)
    if idx_km is None:
        raise ColumnaFaltanteError("No se encontró la columna exacta 'Kilometraje'")
    indice["km_ultimo_servicio"] = idx_km

    return indice


def leer_registros(excel_bytes: bytes) -> list[RegistroCliente]:
    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes), data_only=True, read_only=True)
    if HOJA_ESPERADA not in wb.sheetnames:
        raise ColumnaFaltanteError(f"No existe la hoja '{HOJA_ESPERADA}'")
    hoja = wb[HOJA_ESPERADA]

    filas = hoja.iter_rows(values_only=True)
    cabeceras = [str(c) if c is not None else "" for c in next(filas)]
    indice = _construir_indice_columnas(cabeceras)

    registros: list[RegistroCliente] = []
    for fila in filas:
        matricula = str(fila[indice["matricula"]] or "").strip()
        if not matricula:
            continue

        registros.append(
            RegistroCliente(
                matricula=matricula,
                descripcion=str(fila[indice["descripcion"]] or ""),
                municipio=str(fila[indice["municipio"]] or ""),
                fecha_matriculacion=parsear_fecha(fila[indice["fecha_matriculacion"]]),
                fecha_servicio=parsear_fecha(fila[indice["fecha_servicio"]]),
                km_ultimo_servicio=_a_numero(fila[indice["km_ultimo_servicio"]]),
                km_mantenimiento=_a_numero(fila[indice["km_mantenimiento"]]),
                codigo_servicio=str(fila[indice["codigo_servicio"]] or "").strip(),
                fin_mantenimiento=parsear_fecha(fila[indice["fin_mantenimiento"]]),
                fecha_exp_garantia=parsear_fecha(fila[indice["fecha_exp_garantia"]]),
                inicio_garantia_extendida=parsear_fecha(fila[indice["inicio_garantia_extendida"]]),
                saludo=str(fila[indice["saludo"]] or ""),
                telefono=str(fila[indice["telefono"]] or ""),
                email=str(fila[indice["email"]] or ""),
            )
        )

    return registros


def _a_numero(valor) -> Optional[float]:
    if valor is None or valor == "":
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None
```

- [ ] **Step 4: Ejecutar y comprobar que pasa**

Run: `pytest Flick/SegmentacionCampanas/tests/test_excel_reader.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add Flick/SegmentacionCampanas/excel_reader.py Flick/SegmentacionCampanas/tests/test_excel_reader.py
git commit -m "feat(segmentacion): lector de Excel con detección de columnas por nombre normalizado"
```

---

### Task 6: Deduplicación por matrícula

**Files:**
- Create: `Flick/SegmentacionCampanas/dedup.py`
- Test: `Flick/SegmentacionCampanas/tests/test_dedup.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# Flick/SegmentacionCampanas/tests/test_dedup.py
from datetime import date

from models import RegistroCliente
from dedup import deduplicar_por_matricula_ultima_visita, deduplicar_por_matricula_ultima_fila


def _registro(matricula: str, fecha_servicio: date) -> RegistroCliente:
    return RegistroCliente(
        matricula=matricula, descripcion="NMAX", municipio="Telde",
        fecha_servicio=fecha_servicio,
    )


def test_conserva_la_visita_mas_reciente_por_matricula():
    registros = [
        _registro("AAA", date(2023, 1, 1)),
        _registro("AAA", date(2024, 6, 1)),
        _registro("BBB", date(2022, 3, 3)),
    ]

    resultado = deduplicar_por_matricula_ultima_visita(registros)

    assert len(resultado) == 2
    aaa = next(r for r in resultado if r.matricula == "AAA")
    assert aaa.fecha_servicio == date(2024, 6, 1)


def test_conserva_la_ultima_fila_leida_por_matricula():
    registros = [
        _registro("AAA", date(2023, 1, 1)),
        _registro("AAA", date(2020, 1, 1)),  # fecha anterior, pero es la última fila
    ]

    resultado = deduplicar_por_matricula_ultima_fila(registros)

    assert len(resultado) == 1
    assert resultado[0].fecha_servicio == date(2020, 1, 1)
```

- [ ] **Step 2: Ejecutar y comprobar que falla**

Run: `pytest Flick/SegmentacionCampanas/tests/test_dedup.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'dedup'`

- [ ] **Step 3: Implementar `dedup.py`**

```python
# Flick/SegmentacionCampanas/dedup.py
from datetime import date

from models import RegistroCliente


def deduplicar_por_matricula_ultima_visita(
    registros: list[RegistroCliente],
) -> list[RegistroCliente]:
    """Usado por 3M, 24M, 36M, 46M: si hay varias visitas de la misma
    matrícula, se conserva la de fecha_servicio más reciente."""
    por_matricula: dict[str, RegistroCliente] = {}
    for r in registros:
        actual = por_matricula.get(r.matricula)
        fecha_actual = actual.fecha_servicio if actual else None
        fecha_nueva = r.fecha_servicio
        if actual is None or _es_mas_reciente(fecha_nueva, fecha_actual):
            por_matricula[r.matricula] = r
    return list(por_matricula.values())


def deduplicar_por_matricula_ultima_fila(
    registros: list[RegistroCliente],
) -> list[RegistroCliente]:
    """Usado por 16M: se queda con la última fila del Excel para esa
    matrícula, sin comparar fechas (así lo hace el .osts real: un Map que se
    sobreescribe según el orden de lectura)."""
    por_matricula: dict[str, RegistroCliente] = {}
    for r in registros:
        por_matricula[r.matricula] = r
    return list(por_matricula.values())


def _es_mas_reciente(candidata: date | None, actual: date | None) -> bool:
    if candidata is None:
        return False
    if actual is None:
        return True
    return candidata > actual
```

- [ ] **Step 4: Ejecutar y comprobar que pasa**

Run: `pytest Flick/SegmentacionCampanas/tests/test_dedup.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add Flick/SegmentacionCampanas/dedup.py Flick/SegmentacionCampanas/tests/test_dedup.py
git commit -m "feat(segmentacion): deduplicación por matrícula (dos variantes según campaña)"
```

---

### Task 7: Campaña 3M

**Files:**
- Create: `Flick/SegmentacionCampanas/campanas/__init__.py`
- Create: `Flick/SegmentacionCampanas/campanas/campana_3m.py`
- Test: `Flick/SegmentacionCampanas/tests/test_campana_3m.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# Flick/SegmentacionCampanas/tests/test_campana_3m.py
from datetime import date, timedelta

from models import RegistroCliente
from campanas.campana_3m import filtrar_3m

HOY = date(2026, 7, 21)


def _registro(**overrides) -> RegistroCliente:
    base = dict(
        matricula="1234ABC", descripcion="Yamaha NMAX 125", municipio="Telde",
        fecha_matriculacion=date(2023, 1, 1),
        fecha_servicio=HOY - timedelta(days=200),  # > 3 meses atrás
        km_ultimo_servicio=50,
    )
    base.update(overrides)
    return RegistroCliente(**base)


def test_incluye_vehiculo_sin_visita_hace_mas_de_3_meses_y_km_bajo():
    registros = [_registro()]
    resultado = filtrar_3m(registros, hoy=HOY)
    assert len(resultado) == 1


def test_excluye_por_kilometraje_alto():
    registros = [_registro(km_ultimo_servicio=500)]
    resultado = filtrar_3m(registros, hoy=HOY)
    assert resultado == []


def test_excluye_visita_reciente_menos_de_3_meses():
    registros = [_registro(fecha_servicio=HOY - timedelta(days=10))]
    resultado = filtrar_3m(registros, hoy=HOY)
    assert resultado == []


def test_no_aplica_fecha_minima_2019_ni_codigos_excluidos():
    # Matriculación en 2015 y código PRE: en 3M NO se descartan por esto.
    registros = [_registro(fecha_matriculacion=date(2015, 1, 1), codigo_servicio="PRE")]
    resultado = filtrar_3m(registros, hoy=HOY)
    assert len(resultado) == 1


def test_deduplica_conservando_la_visita_mas_reciente():
    registros = [
        _registro(fecha_servicio=HOY - timedelta(days=400)),
        _registro(fecha_servicio=HOY - timedelta(days=200)),
    ]
    resultado = filtrar_3m(registros, hoy=HOY)
    assert len(resultado) == 1
    assert resultado[0].fecha_servicio == HOY - timedelta(days=200)
```

- [ ] **Step 2: Ejecutar y comprobar que falla**

Run: `pytest Flick/SegmentacionCampanas/tests/test_campana_3m.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'campanas'`

- [ ] **Step 3: Crear `campanas/__init__.py` vacío**

- [ ] **Step 4: Implementar `campanas/campana_3m.py`**

```python
# Flick/SegmentacionCampanas/campanas/campana_3m.py
from datetime import date

from models import RegistroCliente
from filtros_globales import cumple_filtros_globales
from dedup import deduplicar_por_matricula_ultima_visita
from utils import restar_meses_estilo_js

KM_MAXIMO_ULTIMO_SERVICIO = 200


def filtrar_3m(registros: list[RegistroCliente], *, hoy: date) -> list[RegistroCliente]:
    """Réplica exacta de FiltrarSinVisita3Meses(csv).osts: NO aplica fecha
    mínima 2019 ni códigos excluidos (ver tabla de criterios en el plan).
    Usa restar_meses_estilo_js (no relativedelta) para replicar el overflow
    de JS Date.setMonth — ver fix aplicado tras la revisión de Task 7."""
    corte = restar_meses_estilo_js(hoy, 3)

    candidatos = [
        r for r in registros
        if cumple_filtros_globales(r, aplica_fecha_minima=False)
        and r.fecha_matriculacion is not None
        and r.fecha_servicio is not None
    ]

    deduplicados = deduplicar_por_matricula_ultima_visita(candidatos)

    return [
        r for r in deduplicados
        if r.fecha_matriculacion <= corte
        and r.fecha_servicio <= corte
        and (r.km_ultimo_servicio is None or r.km_ultimo_servicio < KM_MAXIMO_ULTIMO_SERVICIO)
    ]
```

- [ ] **Step 5: `restar_meses_estilo_js` ya existe en `utils.py`** — no se necesita `python-dateutil`;
  no tocar `requirements.txt` en este paso.

- [ ] **Step 6: Ejecutar y comprobar que pasa**

Run: `pytest Flick/SegmentacionCampanas/tests/test_campana_3m.py -v`
Expected: PASS (5 tests + regresión de cutoff en fin de mes)

- [ ] **Step 7: Commit**

```bash
git add Flick/SegmentacionCampanas/campanas/__init__.py Flick/SegmentacionCampanas/campanas/campana_3m.py Flick/SegmentacionCampanas/tests/test_campana_3m.py Flick/SegmentacionCampanas/requirements.txt
git commit -m "feat(segmentacion): campaña 3M con paridad exacta respecto al script real"
```

---

### Task 8: Campaña 24M

**Files:**
- Create: `Flick/SegmentacionCampanas/campanas/campana_24m.py`
- Test: `Flick/SegmentacionCampanas/tests/test_campana_24m.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# Flick/SegmentacionCampanas/tests/test_campana_24m.py
from datetime import date, timedelta

from models import RegistroCliente
from campanas.campana_24m import filtrar_24m

HOY = date(2026, 7, 21)


def _registro(**overrides) -> RegistroCliente:
    base = dict(
        matricula="1234ABC", descripcion="Yamaha NMAX 125", municipio="Telde",
        fecha_matriculacion=date(2020, 1, 1),
        fecha_servicio=HOY - timedelta(days=800),  # > 24 meses atrás
        codigo_servicio="OK1",
    )
    base.update(overrides)
    return RegistroCliente(**base)


def test_incluye_vehiculo_sin_visita_hace_mas_de_24_meses():
    resultado = filtrar_24m([_registro()], hoy=HOY)
    assert len(resultado) == 1


def test_excluye_visita_reciente():
    resultado = filtrar_24m([_registro(fecha_servicio=HOY - timedelta(days=30))], hoy=HOY)
    assert resultado == []


def test_excluye_matriculacion_anterior_a_2019():
    resultado = filtrar_24m([_registro(fecha_matriculacion=date(2018, 12, 31))], hoy=HOY)
    assert resultado == []


def test_excluye_codigo_servicio_excluido():
    resultado = filtrar_24m([_registro(codigo_servicio="YGR")], hoy=HOY)
    assert resultado == []


def test_ordena_por_fecha_de_servicio_ascendente():
    registros = [
        _registro(matricula="AAA", fecha_servicio=HOY - timedelta(days=900)),
        _registro(matricula="BBB", fecha_servicio=HOY - timedelta(days=1200)),
    ]
    resultado = filtrar_24m(registros, hoy=HOY)
    assert [r.matricula for r in resultado] == ["BBB", "AAA"]
```

- [ ] **Step 2: Ejecutar y comprobar que falla**

Run: `pytest Flick/SegmentacionCampanas/tests/test_campana_24m.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'campanas.campana_24m'`

- [ ] **Step 3: Implementar `campanas/campana_24m.py`**

```python
# Flick/SegmentacionCampanas/campanas/campana_24m.py
from datetime import date

from models import RegistroCliente
from filtros_globales import cumple_filtros_globales, tiene_codigo_excluido
from dedup import deduplicar_por_matricula_ultima_visita
from utils import restar_meses_estilo_js


def filtrar_24m(registros: list[RegistroCliente], *, hoy: date) -> list[RegistroCliente]:
    """Réplica exacta de Fecha24MesesSinVisita(CSV).osts. Usa
    restar_meses_estilo_js (no relativedelta) — ver fix de Task 7. El código
    excluido se comprueba DESPUÉS de deduplicar, igual que en el script real
    — ver fix de Task 8 (comprobarlo antes permitía que una matrícula cuya
    visita más reciente tiene código excluido cayera a una visita anterior)."""
    corte = restar_meses_estilo_js(hoy, 24)

    candidatos = [
        r for r in registros
        if cumple_filtros_globales(r, aplica_fecha_minima=True)
        and r.fecha_matriculacion is not None
        and r.fecha_servicio is not None
    ]

    deduplicados = deduplicar_por_matricula_ultima_visita(candidatos)

    finales = [
        r for r in deduplicados
        if r.fecha_servicio <= corte and not tiene_codigo_excluido(r)
    ]

    return sorted(finales, key=lambda r: r.fecha_servicio)
```

- [ ] **Step 4: Ejecutar y comprobar que pasa**

Run: `pytest Flick/SegmentacionCampanas/tests/test_campana_24m.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add Flick/SegmentacionCampanas/campanas/campana_24m.py Flick/SegmentacionCampanas/tests/test_campana_24m.py
git commit -m "feat(segmentacion): campaña 24M con paridad exacta respecto al script real"
```

---

### Task 9: Campaña 16M garantía

**Files:**
- Create: `Flick/SegmentacionCampanas/campanas/campana_16m_garantia.py`
- Test: `Flick/SegmentacionCampanas/tests/test_campana_16m_garantia.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# Flick/SegmentacionCampanas/tests/test_campana_16m_garantia.py
from datetime import date, timedelta

from models import RegistroCliente
from campanas.campana_16m_garantia import filtrar_16m_garantia

HOY = date(2026, 7, 21)


def _registro(**overrides) -> RegistroCliente:
    base = dict(
        matricula="1234ABC", descripcion="Yamaha NMAX 125", municipio="Telde",
        fecha_matriculacion=HOY - timedelta(days=460),  # ~15.1 meses atrás
        inicio_garantia_extendida=None,
    )
    base.update(overrides)
    return RegistroCliente(**base)


def test_incluye_matriculacion_en_ventana_15_16_meses_sin_garantia_extendida():
    resultado = filtrar_16m_garantia([_registro()], hoy=HOY)
    assert len(resultado) == 1


def test_excluye_si_ya_tiene_garantia_extendida_iniciada():
    resultado = filtrar_16m_garantia(
        [_registro(inicio_garantia_extendida=date(2025, 1, 1))], hoy=HOY
    )
    assert resultado == []


def test_excluye_matriculacion_fuera_de_ventana_muy_reciente():
    resultado = filtrar_16m_garantia(
        [_registro(fecha_matriculacion=HOY - timedelta(days=60))], hoy=HOY
    )
    assert resultado == []


def test_excluye_matriculacion_fuera_de_ventana_muy_antigua():
    resultado = filtrar_16m_garantia(
        [_registro(fecha_matriculacion=HOY - timedelta(days=900))], hoy=HOY
    )
    assert resultado == []


def test_deduplica_quedandose_con_la_ultima_fila_leida():
    registros = [
        _registro(matricula="AAA", fecha_matriculacion=HOY - timedelta(days=455)),
        _registro(matricula="AAA", fecha_matriculacion=HOY - timedelta(days=465)),
    ]
    resultado = filtrar_16m_garantia(registros, hoy=HOY)
    assert len(resultado) == 1
    assert resultado[0].fecha_matriculacion == HOY - timedelta(days=465)
```

- [ ] **Step 2: Ejecutar y comprobar que falla**

Run: `pytest Flick/SegmentacionCampanas/tests/test_campana_16m_garantia.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'campanas.campana_16m_garantia'`

- [ ] **Step 3: Implementar `campanas/campana_16m_garantia.py`**

```python
# Flick/SegmentacionCampanas/campanas/campana_16m_garantia.py
from datetime import date

from models import RegistroCliente
from filtros_globales import cumple_filtros_globales
from dedup import deduplicar_por_matricula_ultima_fila
from utils import restar_meses_estilo_js


def filtrar_16m_garantia(registros: list[RegistroCliente], *, hoy: date) -> list[RegistroCliente]:
    """Réplica exacta de '16 m garantía ±30d.osts'. Ventana de matriculación
    de 15 a 16 meses atrás (campaña de venta proactiva de garantía extendida,
    ver spec §1 — el nombre "16M garantía" NO se refiere a la fecha de
    expiración de garantía, sino a los meses desde la matriculación). Usa
    restar_meses_estilo_js (no relativedelta) — ver fix de Task 7, el script
    real también usa setMonth() y por tanto tiene el mismo overflow."""
    desde = restar_meses_estilo_js(hoy, 16)
    hasta = restar_meses_estilo_js(hoy, 15)

    candidatos = [
        r for r in registros
        if cumple_filtros_globales(r, aplica_fecha_minima=False)
        and r.fecha_matriculacion is not None
        and desde <= r.fecha_matriculacion < hasta
        and r.inicio_garantia_extendida is None
    ]

    return deduplicar_por_matricula_ultima_fila(candidatos)
```

- [ ] **Step 4: Ejecutar y comprobar que pasa**

Run: `pytest Flick/SegmentacionCampanas/tests/test_campana_16m_garantia.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add Flick/SegmentacionCampanas/campanas/campana_16m_garantia.py Flick/SegmentacionCampanas/tests/test_campana_16m_garantia.py
git commit -m "feat(segmentacion): campaña 16M garantía con paridad exacta respecto al script real"
```

---

### Task 10: Campañas 36M y 46M/Pre-ITV (sin script real — desde el PDF)

**Files:**
- Create: `Flick/SegmentacionCampanas/campanas/campana_36m.py`
- Create: `Flick/SegmentacionCampanas/campanas/campana_46m_preitv.py`
- Test: `Flick/SegmentacionCampanas/tests/test_campana_36m.py`
- Test: `Flick/SegmentacionCampanas/tests/test_campana_46m_preitv.py`

**⚠️ Importante:** estas dos campañas NO tienen script real de referencia. Se implementan
siguiendo el criterio "principal" descrito en el PDF (misma forma que 24M: sin visita hace
más de X meses), aplicando los filtros globales completos como asunción segura. **Deben
validarse manualmente contra el Excel real con alguien de Flick antes de sustituir el
proceso en producción** (spec §8).

- [ ] **Step 1: Escribir el test que falla para 36M**

```python
# Flick/SegmentacionCampanas/tests/test_campana_36m.py
from datetime import date, timedelta

from models import RegistroCliente
from campanas.campana_36m import filtrar_36m

HOY = date(2026, 7, 21)


def _registro(**overrides) -> RegistroCliente:
    base = dict(
        matricula="1234ABC", descripcion="Yamaha NMAX 125", municipio="Telde",
        fecha_matriculacion=date(2020, 1, 1),
        fecha_servicio=HOY - timedelta(days=1200),  # > 36 meses atrás
        codigo_servicio="OK1",
    )
    base.update(overrides)
    return RegistroCliente(**base)


def test_incluye_vehiculo_sin_visita_hace_mas_de_36_meses():
    resultado = filtrar_36m([_registro()], hoy=HOY)
    assert len(resultado) == 1


def test_excluye_visita_reciente():
    resultado = filtrar_36m([_registro(fecha_servicio=HOY - timedelta(days=100))], hoy=HOY)
    assert resultado == []


def test_ordena_por_fecha_de_servicio_ascendente():
    registros = [
        _registro(matricula="AAA", fecha_servicio=HOY - timedelta(days=1300)),
        _registro(matricula="BBB", fecha_servicio=HOY - timedelta(days=1500)),
    ]
    resultado = filtrar_36m(registros, hoy=HOY)
    assert [r.matricula for r in resultado] == ["BBB", "AAA"]
```

- [ ] **Step 2: Ejecutar y comprobar que falla**

Run: `pytest Flick/SegmentacionCampanas/tests/test_campana_36m.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'campanas.campana_36m'`

- [ ] **Step 3: Implementar `campanas/campana_36m.py`**

```python
# Flick/SegmentacionCampanas/campanas/campana_36m.py
from datetime import date

from models import RegistroCliente
from filtros_globales import cumple_filtros_globales, tiene_codigo_excluido
from dedup import deduplicar_por_matricula_ultima_visita
from utils import restar_meses_estilo_js


def filtrar_36m(registros: list[RegistroCliente], *, hoy: date) -> list[RegistroCliente]:
    """Implementada solo a partir del PDF (§5, Campaña 36M) — SIN script real
    de referencia. Validar manualmente antes de producción (spec §8). Usa
    restar_meses_estilo_js (no relativedelta) — ver fix de Task 7. Por
    consistencia con 24M (única campaña con script real que comparte esta
    forma), el código excluido se comprueba DESPUÉS de deduplicar — ver fix
    de Task 8. Confirmar este supuesto en la validación manual de Task 15."""
    corte = restar_meses_estilo_js(hoy, 36)

    candidatos = [
        r for r in registros
        if cumple_filtros_globales(r, aplica_fecha_minima=True)
        and r.fecha_matriculacion is not None
        and r.fecha_servicio is not None
    ]

    deduplicados = deduplicar_por_matricula_ultima_visita(candidatos)
    finales = [
        r for r in deduplicados
        if r.fecha_servicio <= corte and not tiene_codigo_excluido(r)
    ]

    return sorted(finales, key=lambda r: r.fecha_servicio)
```

- [ ] **Step 4: Ejecutar y comprobar que pasa**

Run: `pytest Flick/SegmentacionCampanas/tests/test_campana_36m.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Escribir el test que falla para 46M/Pre-ITV**

```python
# Flick/SegmentacionCampanas/tests/test_campana_46m_preitv.py
from datetime import date, timedelta

from models import RegistroCliente
from campanas.campana_46m_preitv import filtrar_46m_preitv

HOY = date(2026, 7, 21)


def _registro(**overrides) -> RegistroCliente:
    base = dict(
        matricula="1234ABC", descripcion="Yamaha NMAX 125", municipio="Telde",
        fecha_matriculacion=date(2020, 1, 1),
        fecha_servicio=HOY - timedelta(days=1450),  # > 46 meses atrás
        codigo_servicio="OK1",
    )
    base.update(overrides)
    return RegistroCliente(**base)


def test_incluye_vehiculo_sin_visita_hace_mas_de_46_meses():
    resultado = filtrar_46m_preitv([_registro()], hoy=HOY)
    assert len(resultado) == 1


def test_excluye_visita_reciente():
    resultado = filtrar_46m_preitv([_registro(fecha_servicio=HOY - timedelta(days=200))], hoy=HOY)
    assert resultado == []
```

- [ ] **Step 6: Ejecutar y comprobar que falla**

Run: `pytest Flick/SegmentacionCampanas/tests/test_campana_46m_preitv.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'campanas.campana_46m_preitv'`

- [ ] **Step 7: Implementar `campanas/campana_46m_preitv.py`**

```python
# Flick/SegmentacionCampanas/campanas/campana_46m_preitv.py
from datetime import date

from models import RegistroCliente
from filtros_globales import cumple_filtros_globales, tiene_codigo_excluido
from dedup import deduplicar_por_matricula_ultima_visita
from utils import restar_meses_estilo_js


def filtrar_46m_preitv(registros: list[RegistroCliente], *, hoy: date) -> list[RegistroCliente]:
    """Implementada solo a partir del PDF (§5, Campaña 46M/Pre-ITV) — SIN
    script real de referencia. Validar manualmente antes de producción. Usa
    restar_meses_estilo_js (no relativedelta) — ver fix de Task 7. Código
    excluido comprobado DESPUÉS de deduplicar, por consistencia con 24M —
    ver fix de Task 8. Confirmar en la validación manual de Task 15."""
    corte = restar_meses_estilo_js(hoy, 46)

    candidatos = [
        r for r in registros
        if cumple_filtros_globales(r, aplica_fecha_minima=True)
        and r.fecha_matriculacion is not None
        and r.fecha_servicio is not None
    ]

    deduplicados = deduplicar_por_matricula_ultima_visita(candidatos)
    finales = [
        r for r in deduplicados
        if r.fecha_servicio <= corte and not tiene_codigo_excluido(r)
    ]

    return sorted(finales, key=lambda r: r.fecha_servicio)
```

- [ ] **Step 8: Ejecutar y comprobar que pasa**

Run: `pytest Flick/SegmentacionCampanas/tests/test_campana_46m_preitv.py -v`
Expected: PASS (2 tests)

- [ ] **Step 9: Commit**

```bash
git add Flick/SegmentacionCampanas/campanas/campana_36m.py Flick/SegmentacionCampanas/campanas/campana_46m_preitv.py Flick/SegmentacionCampanas/tests/test_campana_36m.py Flick/SegmentacionCampanas/tests/test_campana_46m_preitv.py
git commit -m "feat(segmentacion): campañas 36M y 46M/Pre-ITV desde criterio del PDF (pendiente validación manual)"
```

---

### Task 11: Generador de CSV

**Files:**
- Create: `Flick/SegmentacionCampanas/csv_writer.py`
- Test: `Flick/SegmentacionCampanas/tests/test_csv_writer.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# Flick/SegmentacionCampanas/tests/test_csv_writer.py
from datetime import date

from models import CampanaId, RegistroCliente
from csv_writer import generar_csv, nombre_archivo_csv


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
    assert lineas[1].startswith("2020-01-01;1234ABC;NMAX;2024-01-01;5000")


def test_campana_16m_incluye_columnas_de_garantia():
    registro = RegistroCliente(
        matricula="1234ABC", descripcion="NMAX", municipio="Telde",
        fecha_matriculacion=date(2020, 1, 1),
        fecha_exp_garantia=date(2022, 1, 1),
    )

    csv_texto = generar_csv([registro], campana=CampanaId.DIECISEIS_MESES_GARANTIA)

    assert "FECHA EXP GARANTIA" in csv_texto.split("\n")[0]
    assert "INICIO GARANT EXTEND" in csv_texto.split("\n")[0]


def test_nombre_archivo_incluye_campana_y_fecha():
    nombre = nombre_archivo_csv(CampanaId.VEINTICUATRO_MESES, hoy=date(2026, 7, 21))
    assert nombre == "FiltradoCampana24M_2026-07-21.csv"
```

- [ ] **Step 2: Ejecutar y comprobar que falla**

Run: `pytest Flick/SegmentacionCampanas/tests/test_csv_writer.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'csv_writer'`

- [ ] **Step 3: Implementar `csv_writer.py`**

```python
# Flick/SegmentacionCampanas/csv_writer.py
from datetime import date

from models import CampanaId, RegistroCliente

CABECERAS_BASE = [
    "FECHA MATRICULACION", "N MATRICULA", "DESCRIPCION", "FECHA DE SERVICIO",
    "KILOMETRAJE ULTIMO SERVICIO", "CODIGO SERVICIO", "KILOMETRAJE MANTENIMIENTO",
    "FIN MANTENIMIENTO", "SALUDO", "TELEFONO", "EMAIL", "DIRECCION",
]

CABECERAS_GARANTIA_EXTRA = ["FECHA EXP GARANTIA", "INICIO GARANT EXTEND"]


def _cabeceras_para(campana: CampanaId) -> list[str]:
    if campana == CampanaId.DIECISEIS_MESES_GARANTIA:
        base = CABECERAS_BASE[:8]
        return base + CABECERAS_GARANTIA_EXTRA + CABECERAS_BASE[8:]
    return CABECERAS_BASE


def _valor_campo(registro: RegistroCliente, cabecera: str) -> str:
    mapa = {
        "FECHA MATRICULACION": registro.fecha_matriculacion,
        "N MATRICULA": registro.matricula,
        "DESCRIPCION": registro.descripcion,
        "FECHA DE SERVICIO": registro.fecha_servicio,
        "KILOMETRAJE ULTIMO SERVICIO": registro.km_ultimo_servicio,
        "CODIGO SERVICIO": registro.codigo_servicio,
        "KILOMETRAJE MANTENIMIENTO": registro.km_mantenimiento,
        "FIN MANTENIMIENTO": registro.fin_mantenimiento,
        "FECHA EXP GARANTIA": registro.fecha_exp_garantia,
        "INICIO GARANT EXTEND": registro.inicio_garantia_extendida,
        "SALUDO": registro.saludo,
        "TELEFONO": registro.telefono,
        "EMAIL": registro.email,
        "DIRECCION": registro.municipio,
    }
    valor = mapa.get(cabecera)
    texto = "" if valor is None else str(valor)
    return texto.replace(";", ",")


def generar_csv(registros: list[RegistroCliente], *, campana: CampanaId) -> str:
    cabeceras = _cabeceras_para(campana)
    lineas = [";".join(cabeceras)]
    for r in registros:
        lineas.append(";".join(_valor_campo(r, c) for c in cabeceras))
    return "\n".join(lineas)


def nombre_archivo_csv(campana: CampanaId, *, hoy: date) -> str:
    return f"FiltradoCampana{campana.value}_{hoy.isoformat()}.csv"
```

- [ ] **Step 4: Ejecutar y comprobar que pasa**

Run: `pytest Flick/SegmentacionCampanas/tests/test_csv_writer.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add Flick/SegmentacionCampanas/csv_writer.py Flick/SegmentacionCampanas/tests/test_csv_writer.py
git commit -m "feat(segmentacion): generador de CSV con formato idéntico al actual"
```

---

### Task 12: Subida a Blob Storage + SAS

**Files:**
- Create: `Flick/SegmentacionCampanas/blob_storage.py`
- Test: `Flick/SegmentacionCampanas/tests/test_blob_storage.py`

Se usa un mock del SDK de Azure Storage — no se necesita una cuenta real para testear
la lógica de negocio (nombre de blob, expiración del SAS).

- [ ] **Step 1: Escribir el test que falla**

```python
# Flick/SegmentacionCampanas/tests/test_blob_storage.py
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from blob_storage import subir_csv_y_generar_link

CONNECTION_STRING = "UseDevelopmentStorage=true"
CONTAINER = "csv-campanas"


@patch("blob_storage.generate_blob_sas", return_value="firma-sas-fake")
@patch("blob_storage.BlobServiceClient.from_connection_string")
def test_sube_el_csv_y_devuelve_url_con_sas(mock_from_conn, mock_generate_sas):
    mock_client = MagicMock()
    mock_from_conn.return_value = mock_client
    mock_blob_client = mock_client.get_blob_client.return_value
    mock_blob_client.url = "https://cuenta.blob.core.windows.net/csv-campanas/archivo.csv"
    mock_client.credential.account_key = "clave-fake"

    url = subir_csv_y_generar_link(
        csv_contenido="a;b\n1;2",
        nombre_archivo="FiltradoCampana3M_2026-07-21.csv",
        connection_string=CONNECTION_STRING,
        container=CONTAINER,
        horas_expiracion=24,
    )

    mock_blob_client.upload_blob.assert_called_once()
    assert url.startswith("https://cuenta.blob.core.windows.net/csv-campanas/archivo.csv?")
    assert "firma-sas-fake" in url
```

- [ ] **Step 2: Ejecutar y comprobar que falla**

Run: `pytest Flick/SegmentacionCampanas/tests/test_blob_storage.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'blob_storage'`

- [ ] **Step 3: Implementar `blob_storage.py`**

```python
# Flick/SegmentacionCampanas/blob_storage.py
from datetime import datetime, timedelta, timezone

from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas


def subir_csv_y_generar_link(
    *,
    csv_contenido: str,
    nombre_archivo: str,
    connection_string: str,
    container: str,
    horas_expiracion: int = 24,
) -> str:
    """Sube el CSV a Blob Storage y devuelve una URL de solo lectura con SAS
    de expiración corta. No se loguea el contenido del CSV (contiene PII)."""
    cliente_servicio = BlobServiceClient.from_connection_string(connection_string)
    cliente_blob = cliente_servicio.get_blob_client(container=container, blob=nombre_archivo)

    cliente_blob.upload_blob(
        csv_contenido.encode("utf-8"),
        overwrite=True,
        content_settings=None,
    )

    expiracion = datetime.now(timezone.utc) + timedelta(hours=horas_expiracion)
    sas = generate_blob_sas(
        account_name=cliente_servicio.account_name,
        container_name=container,
        blob_name=nombre_archivo,
        account_key=cliente_servicio.credential.account_key,
        permission=BlobSasPermissions(read=True),
        expiry=expiracion,
    )

    return f"{cliente_blob.url}?{sas}"
```

- [ ] **Step 4: Ejecutar y comprobar que pasa**

Run: `pytest Flick/SegmentacionCampanas/tests/test_blob_storage.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Commit**

```bash
git add Flick/SegmentacionCampanas/blob_storage.py Flick/SegmentacionCampanas/tests/test_blob_storage.py
git commit -m "feat(segmentacion): subida de CSV a Blob Storage con SAS de lectura temporal"
```

---

### Task 13: Endpoint HTTP completo

**Files:**
- Modify: `Flick/SegmentacionCampanas/function_app.py`
- Create: `Flick/SegmentacionCampanas/campanas/motor.py`
- Test: `Flick/SegmentacionCampanas/tests/test_motor.py`
- Test: `Flick/SegmentacionCampanas/tests/test_function_app.py`

- [ ] **Step 1: Escribir el test que falla para el motor (dispatch por campaña)**

```python
# Flick/SegmentacionCampanas/tests/test_motor.py
from datetime import date
import io

import openpyxl
import pytest

from models import CampanaId
from campanas.motor import ejecutar_campana, CampanaNoSoportadaError

COLUMNAS = [
    "Nº.matrícula", "Descripción", "Direccion(3)", "Fecha.matriculación",
    "Fecha.de.servicio", "Kilometraje", "Kilometraje.mantenim",
    "Código.de.servicio(1)", "Fin.mantenimiento", "Fecha.exp.garantia",
    "Inicio.garant.extend", "Saludo.(tratamiento)", "Nº.telefono(4)",
    "Direccion.e-mail",
]


def _excel_con_una_fila_valida_3m() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Hoja1"
    ws.append(COLUMNAS)
    ws.append([
        "1234ABC", "Yamaha NMAX 125", "Telde", date(2023, 1, 1),
        date(2020, 1, 1), 50, 10000, "OK1", "--/--/--", "--/--/--",
        "--/--/--", "Sr.", "600123456", "cliente@example.com",
    ])
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def test_ejecutar_campana_3m_devuelve_registros_y_csv():
    excel_bytes = _excel_con_una_fila_valida_3m()

    resultado = ejecutar_campana(CampanaId.TRES_MESES, excel_bytes, hoy=date(2026, 7, 21))

    assert resultado.total_clientes == 1
    assert "1234ABC" in resultado.csv_contenido
    assert resultado.nombre_archivo == "FiltradoCampana3M_2026-07-21.csv"


def test_campana_no_soportada_lanza_error():
    with pytest.raises(CampanaNoSoportadaError):
        ejecutar_campana("NO-EXISTE", b"", hoy=date(2026, 7, 21))
```

- [ ] **Step 2: Ejecutar y comprobar que falla**

Run: `pytest Flick/SegmentacionCampanas/tests/test_motor.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'campanas.motor'`

- [ ] **Step 3: Implementar `campanas/motor.py`**

```python
# Flick/SegmentacionCampanas/campanas/motor.py
from dataclasses import dataclass
from datetime import date

from models import CampanaId
from excel_reader import leer_registros
from csv_writer import generar_csv, nombre_archivo_csv

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
    nombre_archivo = nombre_archivo_csv(campana, hoy=hoy)

    return ResultadoCampana(
        total_clientes=len(resultado),
        csv_contenido=csv_contenido,
        nombre_archivo=nombre_archivo,
    )
```

- [ ] **Step 4: Ejecutar y comprobar que pasa**

Run: `pytest Flick/SegmentacionCampanas/tests/test_motor.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Escribir el test que falla para `function_app.py`**

```python
# Flick/SegmentacionCampanas/tests/test_function_app.py
import json
from unittest.mock import patch

import azure.functions as func

from function_app import segmentar_campana


def _request(campana: str | None, body: bytes = b"") -> func.HttpRequest:
    params = {"campana": campana} if campana else {}
    return func.HttpRequest(
        method="POST", url="/api/segmentar_campana", params=params, body=body
    )


def test_falta_parametro_campana_devuelve_400():
    respuesta = segmentar_campana(_request(campana=None, body=b"contenido"))
    assert respuesta.status_code == 400


def test_cuerpo_vacio_devuelve_400():
    respuesta = segmentar_campana(_request(campana="3M", body=b""))
    assert respuesta.status_code == 400


def test_campana_desconocida_devuelve_400():
    respuesta = segmentar_campana(_request(campana="NO-EXISTE", body=b"contenido"))
    assert respuesta.status_code == 400


@patch("function_app.subir_csv_y_generar_link", return_value="https://fake/url?sas=1")
@patch("function_app.ejecutar_campana")
def test_ejecucion_correcta_devuelve_200_con_link(mock_ejecutar, mock_subir):
    from campanas.motor import ResultadoCampana

    mock_ejecutar.return_value = ResultadoCampana(
        total_clientes=3, csv_contenido="a;b\n1;2", nombre_archivo="Filtrado.csv"
    )

    respuesta = segmentar_campana(_request(campana="3M", body=b"excel-binario"))

    assert respuesta.status_code == 200
    cuerpo = json.loads(respuesta.get_body())
    assert cuerpo["total_clientes"] == 3
    assert cuerpo["download_url"] == "https://fake/url?sas=1"
```

- [ ] **Step 6: Ejecutar y comprobar que falla**

Run: `pytest Flick/SegmentacionCampanas/tests/test_function_app.py -v`
Expected: FAIL (la función actual devuelve 501 siempre)

- [ ] **Step 7: Implementar `function_app.py` completo**

```python
# Flick/SegmentacionCampanas/function_app.py
import json
import logging
import os
from datetime import date, datetime, timezone

import azure.functions as func

from campanas.motor import ejecutar_campana, CampanaNoSoportadaError
from blob_storage import subir_csv_y_generar_link

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.route(route="segmentar_campana", methods=["POST"])
def segmentar_campana(req: func.HttpRequest) -> func.HttpResponse:
    campana_id = req.params.get("campana")
    if not campana_id:
        return _error(400, "campana_requerida", "Falta el parámetro 'campana'.")

    excel_bytes = req.get_body()
    if not excel_bytes:
        return _error(400, "excel_vacio", "El cuerpo de la petición está vacío.")

    try:
        resultado = ejecutar_campana(campana_id, excel_bytes, hoy=datetime.now(timezone.utc).date())
    except CampanaNoSoportadaError:
        return _error(400, "campana_desconocida", f"Campaña no soportada: '{campana_id}'.")
    except Exception:
        logging.exception("segmentar_campana: error procesando el Excel (campaña=%s)", campana_id)
        return _error(500, "error_procesamiento", "No se pudo procesar el Excel maestro.")

    if resultado.total_clientes == 0:
        return func.HttpResponse(
            json.dumps({"total_clientes": 0, "download_url": None}),
            status_code=200,
            mimetype="application/json",
        )

    try:
        download_url = subir_csv_y_generar_link(
            csv_contenido=resultado.csv_contenido,
            nombre_archivo=resultado.nombre_archivo,
            connection_string=os.environ["BLOB_CONNECTION_STRING"],
            container=os.environ["BLOB_CONTAINER_NAME"],
            horas_expiracion=24,
        )
    except Exception:
        logging.exception("segmentar_campana: error subiendo el CSV a Blob Storage")
        return _error(500, "error_subida_csv", "No se pudo generar el enlace de descarga.")

    logging.info("segmentar_campana: campaña=%s total_clientes=%d", campana_id, resultado.total_clientes)

    return func.HttpResponse(
        json.dumps({"total_clientes": resultado.total_clientes, "download_url": download_url}),
        status_code=200,
        mimetype="application/json",
    )


def _error(status_code: int, codigo: str, mensaje: str) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({"codigo": codigo, "mensaje": mensaje}),
        status_code=status_code,
        mimetype="application/json",
    )
```

- [ ] **Step 8: Ejecutar y comprobar que pasa**

Run: `pytest Flick/SegmentacionCampanas/tests/test_function_app.py -v`
Expected: PASS (4 tests)

- [ ] **Step 9: Ejecutar toda la suite de tests**

Run: `pytest Flick/SegmentacionCampanas/tests/ -v`
Expected: PASS (todos los tests de las Tasks 2-13)

- [ ] **Step 10: Commit**

```bash
git add Flick/SegmentacionCampanas/function_app.py Flick/SegmentacionCampanas/campanas/motor.py Flick/SegmentacionCampanas/tests/test_motor.py Flick/SegmentacionCampanas/tests/test_function_app.py
git commit -m "feat(segmentacion): endpoint HTTP completo — motor + subida a Blob + manejo de errores"
```

---

### Task 14: Auditoría de dependencias y README

**Files:**
- Create: `Flick/SegmentacionCampanas/README.md`
- Modify: `Flick/SegmentacionCampanas/requirements.txt` (ya completo desde Task 7)

- [ ] **Step 1: Ejecutar `pip-audit` (Gate 4 de ssdlc)**

Run: `pip install pip-audit && pip-audit -r Flick/SegmentacionCampanas/requirements.txt`
Expected: sin vulnerabilidades conocidas. Si aparece alguna, actualizar la versión pineada en `requirements.txt` antes de continuar.

- [ ] **Step 2: Crear `README.md` de la función**

```markdown
# SegmentacionCampanas

Azure Function (Python) que sustituye a los Office Scripts de las 5 campañas de
marketing posventa de Flick. Recibe el Excel maestro como binario y un id de
campaña, aplica el motor de filtrado correspondiente, y devuelve un enlace de
descarga (Blob Storage + SAS de 24h) al CSV resultante.

Ver diseño completo en
`../docs/superpowers/specs/2026-07-21-motor-segmentacion-azure-function-design.md`.

## Uso

    POST /api/segmentar_campana?campana=3M&code=<function-key>
    Content-Type: application/octet-stream
    Body: <bytes del .xlsx>

Respuesta:

    { "total_clientes": 42, "download_url": "https://...csv?sv=..." }

Campañas soportadas: `3M`, `24M`, `36M`, `46M`, `16M`.

⚠️ `36M` y `46M` no tienen script real de referencia — su criterio se implementó
solo a partir de la documentación funcional y debe validarse manualmente contra
el Excel real antes de sustituir el proceso actual en producción.

## Desarrollo local

    python -m venv .venv
    .venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    cp local.settings.json.example local.settings.json  # y rellenar los valores
    func start

## Tests

    pip install pytest python-dateutil
    pytest tests/ -v
```

- [ ] **Step 3: Commit**

```bash
git add Flick/SegmentacionCampanas/README.md
git commit -m "docs(segmentacion): README de la función y verificación de dependencias"
```

---

### Task 15: Validación manual contra el Excel real (antes de sustituir producción)

**Files:** ninguno (verificación manual, no código)

Los tests unitarios de las Tasks 7-10 verifican la lógica con datos sintéticos, pero
no sustituyen una comparación real contra el Office Script en producción. Antes de
apagar cualquier Office Script:

- [ ] **Step 1: Generar el CSV con el Office Script real** para 3M, 24M y 16M sobre
  el Excel maestro actual (ejecutar el flujo de Power Automate/Copilot Studio hoy tal
  cual, guardando el CSV descargado de cada una).

- [ ] **Step 2: Ejecutar la Function localmente sobre el mismo Excel**

```bash
func start  # en Flick/SegmentacionCampanas/
curl -X POST "http://localhost:7071/api/segmentar_campana?campana=3M" \
  --data-binary "@../ExcelFlick.xlsx" -H "Content-Type: application/octet-stream"
```

  (repetir para `24M` y `16M`, descargando el CSV de cada `download_url`)

- [ ] **Step 3: Diff fila a fila** entre el CSV del Office Script y el CSV de la
  Function para cada una de las 3 campañas. Deben coincidir exactamente. Si no
  coinciden, el motivo casi siempre será una columna mal mapeada en
  `excel_reader.py` (Task 5) — depurar ahí antes de tocar la lógica de filtrado.

- [ ] **Step 4: Para 36M y 46M/Pre-ITV** (sin script real de referencia), ejecutar la
  Function sobre el Excel real y revisar manualmente una muestra de 10-15 resultados
  con alguien de Flick que conozca el negocio, para confirmar que el criterio
  interpretado del PDF es el correcto — el mismo tipo de discrepancia encontrada en
  16M (spec §1) podría repetirse aquí.

- [ ] **Step 5: Documentar el resultado de la validación** (coincide / no coincide,
  y qué se corrigió) como comentario en el PR o en una nota de seguimiento antes de
  desactivar los Office Scripts equivalentes en producción.

---

## Fuera de alcance de este plan (ver spec §3 y §9)

- Conexión Power Automate → Azure Function (configuración manual en Power Platform,
  no es código de este repo). Pasos: crear la acción HTTP en el flujo de Power
  Automate existente, apuntando a la URL de la Function desplegada, con el body
  binario del Excel y el `code` (function key) como query param.
- Despliegue de la infraestructura Azure (Function App, Storage Account, Container)
  — se recomienda Infra-as-Code (Bicep/Terraform) en un plan aparte si se quiere
  reproducibilidad, o creación manual vía Azure CLI/Portal para un primer despliegue.
- **Lifecycle policy del Blob Storage** (borrado automático a 7 días, spec §6) — es
  configuración de infraestructura, no código de la Function. Ejemplo con Azure CLI:

  ```bash
  az storage account management-policy create \
    --account-name <nombre-cuenta> \
    --policy '{
      "rules": [{
        "enabled": true,
        "name": "borrar-csv-campanas-7-dias",
        "type": "Lifecycle",
        "definition": {
          "actions": { "baseBlob": { "delete": { "daysAfterModificationGreaterThan": 7 } } },
          "filters": { "blobTypes": ["blockBlob"], "prefixMatch": ["csv-campanas/"] }
        }
      }]
    }'
  ```

- Migración de `FiltrarMantenimientoPorHito` / `CalcularMediasKilometraje` (spec §9).
