# NormalizarFecha

Función HTTP de Azure Functions que recibe una fecha en **cualquier formato** (texto libre, distintos idiomas y separadores) y la devuelve normalizada al formato estándar `DD/MM/YYYY`.

## Descripción

Utiliza la librería [`dateparser`](https://dateparser.readthedocs.io/) para interpretar fechas en español e inglés sin importar cómo estén escritas: con texto, abreviaciones, diferentes separadores o incluso expresiones relativas.

### Ejemplos de entrada y salida

| Entrada (`fecha`)       | Salida (`fecha_normalizada`) |
|-------------------------|------------------------------|
| `01/02/2025`            | `01/02/2025`                 |
| `1-febrero-25`          | `01/02/2025`                 |
| `February 1 2025`       | `01/02/2025`                 |
| `1 de febrero de 2025`  | `01/02/2025`                 |
| `2025-02-01`            | `01/02/2025`                 |
| `feb 1, 2025`           | `01/02/2025`                 |

## Endpoint

```
GET/POST /api/normalizar_fecha
```

> Requiere autenticación de nivel **Function** (clave de función en el encabezado o query param `code`).

## Parámetros

La fecha puede enviarse de dos formas:

### 1. Query string (GET o POST)

```
GET /api/normalizar_fecha?fecha=1-febrero-2025&code=<function-key>
```

### 2. Body JSON (POST)

```json
{
  "fecha": "1 de febrero de 2025"
}
```

## Respuestas

### ✅ 200 OK — Fecha normalizada correctamente

```json
{
  "fecha_original": "1 de febrero de 2025",
  "fecha_normalizada": "01/02/2025"
}
```

### ❌ 400 Bad Request — Campo `fecha` ausente

```json
{
  "error": "Falta el campo 'fecha'. Envíalo como query param (?fecha=...) o en el body JSON."
}
```

### ❌ 400 Bad Request — Fecha no reconocida

```json
{
  "error": "No se pudo interpretar la fecha '32/13/2025'. Intenta con formatos como 01/02/2025, 1-febrero-25 o February 1 2025."
}
```

## Configuración del parser

| Parámetro                  | Valor           | Descripción                                           |
|----------------------------|-----------------|-------------------------------------------------------|
| `languages`                | `['es', 'en']`  | Idiomas soportados: español e inglés                  |
| `DATE_ORDER`               | `DMY`           | Orden de día/mes/año para formatos ambiguos           |
| `PREFER_DAY_OF_MONTH`      | `first`         | En fechas sin día, selecciona el primero del mes      |
| `RETURN_AS_TIMEZONE_AWARE` | `False`         | Fechas sin información de zona horaria                |

## Estructura de archivos

```
NormalizarFecha/
├── function_app.py       # Lógica principal de la función
├── host.json             # Configuración del host de Azure Functions
├── local.settings.json   # Variables de entorno locales (no subir a producción)
├── requirements.txt      # Dependencias: azure-functions, dateparser
└── README.md             # Esta documentación
```

## Dependencias

```txt
azure-functions
dateparser
```

Instalación:

```bash
pip install -r requirements.txt
```

## Ejecución local

```bash
# Activar entorno virtual
.venv\Scripts\Activate.ps1   # Windows (PowerShell)

# Iniciar la función
func start
```

La función estará disponible en:

```
http://localhost:7071/api/normalizar_fecha
```

### Prueba rápida con `curl`

```bash
# GET con query string
curl "http://localhost:7071/api/normalizar_fecha?fecha=1-febrero-2025"

# POST con body JSON
curl -X POST http://localhost:7071/api/normalizar_fecha \
  -H "Content-Type: application/json" \
  -d "{\"fecha\": \"1 de febrero de 2025\"}"
```
