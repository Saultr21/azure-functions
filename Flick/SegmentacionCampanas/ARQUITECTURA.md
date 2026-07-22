# Arquitectura — Agente Campañas (Flick)

> Documento de mantenimiento y replicación. Objetivo: que cualquier desarrollador
> (o el propio Saúl dentro de 6 meses) pueda entender, mantener y **replicar este
> sistema completo para otro cliente** sin tener que reconstruir el contexto
> desde cero.
>
> Última actualización: 2026-07-22.

## 1. Qué es esto, en una frase

Un agente conversacional en Microsoft Copilot Studio que el personal del taller
de Flick usa para pedir, en lenguaje natural, la lista de clientes candidatos a
una de 5 campañas de marketing posventa (mantenimiento/garantía) para motos
Yamaha — sustituyendo 5 Office Scripts que antes se ejecutaban manualmente
sobre un Excel.

## 2. Arquitectura de extremo a extremo

```
Usuario (taller Flick)
   │  "genera la lista de la campaña de 3 meses"
   ▼
Agente "Agente Campañas" (Copilot Studio, nueva experiencia)
   │  interpreta la campaña → llama a la tool
   ▼
Workflow "generar_lista_campana" (Copilot Studio, nueva experiencia de workflows)
   │  1. When an agent calls the flow (input: campana, texto)
   │  2. OneDrive "Obtener contenido de archivo" → /ExcelFlick/ExcelFlick.xlsx
   │  3. HTTP POST → Azure Function (Excel + campana + function key)
   │  4. Respond to the agent (total_clientes, download_url, csv_contenido,
   │     nombre_archivo, municipios_no_reconocidos)
   ▼
Azure Function "func-flick-segmentacion" (Python, HTTP trigger)
   │  segmentar_campana(): lee el Excel, aplica el motor de la campaña,
   │  genera CSV (para el chat) + Excel (para descarga), sube el Excel
   │  a Blob Storage con un link SAS de 24h
   ▼
Azure Blob Storage "stflicksegcampanas" (contenedor "csv-campanas")
   │  guarda el .xlsx resultante, con lifecycle policy de borrado a 7 días
   ▼
Respuesta vuelve al agente → se muestra en el chat: tabla Markdown +
total + nombre de archivo + enlace de descarga + aviso de municipios
no reconocidos (si aplica)
```

Ningún componente es Power Automate clásico — ver `DEC-005` en `TODO.md` sobre
por qué se usó el workflow nativo de Copilot Studio en vez de un flujo de Power
Automate separado.

## 3. Componente 1: Azure Function (el motor de negocio)

Vive en `Flick/SegmentacionCampanas/`. Es el único componente con lógica de
negocio real; todo lo demás (agente, workflow) es orquestación y presentación.

### 3.1 Endpoint

```
POST /api/segmentar_campana?campana=<3M|24M|36M|46M|16M>&code=<function-key>
Content-Type: application/octet-stream
Body: <bytes del Excel maestro (.xlsx)>
```

Respuesta 200 (éxito, con o sin candidatos):

```json
{
  "total_clientes": 224,
  "download_url": "https://stflicksegcampanas.blob.core.windows.net/csv-campanas/FiltradoCampana3M_2026-07-22.xlsx?sv=...",
  "nombre_archivo": "FiltradoCampana3M_2026-07-22.xlsx",
  "csv_contenido": "Nº.matrícula;Descripción;...\n1234ABC;YAMAHA NMAX 125;...",
  "municipios_no_reconocidos": {"San Bartolomé de Tirajana": 1200, "(vacío)": 340}
}
```

Si `total_clientes` es 0, `download_url` y `nombre_archivo` son `null` y no se
sube nada a Blob Storage (ver `function_app.py`).

Respuesta 400: `campana_requerida` (falta el parámetro), `campana_desconocida`
(valor no soportado), `excel_vacio` (cuerpo vacío). Respuesta 500:
`error_procesamiento`, `error_subida_excel` — mensajes genéricos, sin volcar la
excepción real al cliente (el detalle va a `logging.exception`, visible en
Application Insights, no en la respuesta HTTP).

### 3.2 Flujo interno (`function_app.py` → `campanas/motor.py`)

1. `excel_reader.leer_registros(excel_bytes)` — parsea el Excel a una lista de
   `RegistroCliente` (Pydantic, `models.py`). Cada fila del Excel se normaliza
   a este modelo tipado; los campos de garantía son opcionales porque solo los
   usa la campaña 16M.
2. Se selecciona la función de filtrado según `CampanaId` (`campanas/campana_*.py`,
   ver tabla de criterios en la sección 4).
3. `csv_writer.generar_csv()` y `excel_writer.generar_excel()` generan las dos
   representaciones del resultado a partir de la MISMA lista de registros
   filtrados — comparten cabeceras y extracción de valores (`cabeceras_para`,
   `valor_campo` en `csv_writer.py`) para que nunca diverjan entre sí.
   - El **CSV** (texto) es solo para renderizar la tabla en el chat — nunca se
     sube a ningún sitio.
   - El **Excel** (bytes) es el único archivo que se sube a Blob Storage y se
     ofrece como descarga.
4. `filtros_globales.municipios_no_reconocidos(registros)` se calcula sobre la
   lista **completa sin filtrar** (antes de aplicar el filtro de campaña) —
   por diseño: es un chequeo de calidad de datos independiente de qué campaña
   se pidió, no un efecto secundario del filtrado.
5. Se devuelve un `ResultadoCampana` (dataclass) con los 5 campos que
   `function_app.py` serializa a JSON.

### 3.3 Filtros globales (`filtros_globales.py`)

Se aplican a TODAS las campañas, antes de la deduplicación:

- **Modelo**: el texto de `descripcion` (limpiado con
  `utils.limpiar_texto_modelo`) debe contener alguno de los 8 modelos válidos
  (`MODELOS_VALIDOS`: nmax, xmax125, xmax300, tmax, mt125, mt07, mt09,
  tenere700).
- **Municipio**: el texto de `municipio` (normalizado con
  `utils.normalizar_texto`, quita acentos/mayúsculas) debe contener alguno de
  los 13 municipios de `MUNICIPIOS_VALIDOS` (todos del norte/centro de Gran
  Canaria — ver **sección 6, hallazgo pendiente de confirmar con Flick**).
- **Fecha mínima de matriculación** (2019-01-01): opcional, se activa por
  campaña con el flag `aplica_fecha_minima` — 3M y 16M NO la aplican, 24M/36M/46M
  sí.

El **código de servicio excluido** (`PRE`, `YGR`, `YIT`) NO forma parte de
`cumple_filtros_globales` — se aplica DESPUÉS de la deduplicación, vía
`tiene_codigo_excluido()`, porque así lo hacen los Office Scripts originales
(ver docstring del módulo). Aplicarlo antes rompería la deduplicación: si la
visita más reciente de una matrícula tiene código excluido, en producción esa
matrícula se descarta entera, no "cae" a una visita anterior válida.

### 3.4 Deduplicación (`dedup.py`)

Dos estrategias, porque los Office Scripts originales las usan de forma
distinta:

- `deduplicar_por_matricula_ultima_visita` (3M, 24M, 36M, 46M): entre varias
  visitas de la misma matrícula, se queda con la de `fecha_servicio` más
  reciente.
- `deduplicar_por_matricula_ultima_fila` (16M): se queda con la última fila del
  Excel para esa matrícula, sin comparar fechas — replica un `Map` de
  JavaScript que se sobreescribe según el orden de lectura del `.osts` real.

### 3.5 Las 5 campañas (`campanas/campana_*.py`)

| Campaña | Función | Fecha mínima 2019 | Ventana | Dedup | Script real de referencia |
|---|---|---|---|---|---|
| 3M | `filtrar_3m` | No | matriculación y servicio ≤ hoy−3 meses, km último servicio < 200 | última visita | Sí (`FiltrarSinVisita3Meses`) |
| 24M | `filtrar_24m` | Sí | servicio ≤ hoy−24 meses, sin código excluido | última visita | Sí (`Fecha24MesesSinVisita`) |
| 36M | `filtrar_36m` | Sí | servicio ≤ hoy−36 meses, sin código excluido | última visita | **No** — solo PDF |
| 46M/Pre-ITV | `filtrar_46m_preitv` | Sí | servicio ≤ hoy−46 meses, sin código excluido | última visita | **No** — solo PDF |
| 16M garantía | `filtrar_16m_garantia` | No | matriculación entre hoy−16 y hoy−15 meses, sin garantía extendida iniciada | última fila | Sí (`16 m garantía ±30d`) |

**36M y 46M no tienen script real de referencia** — se implementaron solo a
partir del PDF funcional y replican el patrón de 24M por consistencia (código
excluido tras dedup). Esto es exactamente lo que bloquea `TASK-015` en
`TODO.md`: sin validación manual contra el negocio, podrían tener reglas
sutilmente distintas a las que Flick espera.

Todas usan `utils.restar_meses_estilo_js()` en vez de
`dateutil.relativedelta` — replica deliberadamente el *overflow* de
`Date.setMonth()` de JavaScript (los scripts originales corren en Office
Scripts/TypeScript), que `relativedelta` no reproduce (clampea fechas
inválidas en vez de desbordar). Ver `DEC-004`/fix de Task 7 en `TODO.md` para
el razonamiento completo.

### 3.6 Infraestructura Azure

- **Resource group**: `flick-segmentacion-rg` (Sweden Central).
- **Function App**: `func-flick-segmentacion` — Linux, Consumption, Python 3.12,
  HTTPS-only, Application Insights auto-creado. Auth level `FUNCTION` (necesita
  `code=<function-key>` en la query string).
- **Storage Account**: `stflicksegcampanas` — HTTPS-only, TLS 1.2 mínimo,
  contenedor privado `csv-campanas` con lifecycle policy de borrado a 7 días.
- **Variables de entorno** (`local.settings.json` en local / App Settings en
  Azure): `BLOB_CONNECTION_STRING`, `BLOB_CONTAINER_NAME`.
- **Despliegue**: `func azure functionapp publish func-flick-segmentacion --python`
  desde `Flick/SegmentacionCampanas/`.

## 4. Componente 2: Workflow de Copilot Studio (`generar_lista_campana`)

Entorno: **AgenteFlick** (tenant `grupoflick.onmicrosoft.com`), environment ID
`d37bf82b-fa89-e1e4-8738-f5d21585ce46`, workflow ID
`22a82161-4984-d223-4dd0-10ec06e14020`. Es un **workflow tool nativo de la
nueva experiencia de Copilot Studio**, no un flujo de Power Automate clásico —
ver `DEC-005` en `TODO.md`. Se edita en
`https://copilotstudio.preview.microsoft.com/environments/<env>/flows/<id>`.

### 4.1 Nodos

1. **When an agent calls the flow** (trigger) — un único input: `campana`
   (texto). El agente lo rellena a partir de la conversación.
2. **Obtener contenido de archivo** (conector OneDrive, conexión
   `sistemas3@grupoflick.onmicrosoft.com`) — lee `/ExcelFlick/ExcelFlick.xlsx`,
   el Excel maestro que mantiene Flick.
3. **HTTP** — `POST https://func-flick-segmentacion.azurewebsites.net/api/segmentar_campana`,
   query `campana=<del trigger>` + `code=<function key>`, header
   `Content-Type: application/octet-stream`, body = contenido binario del
   OneDrive.
4. **Respond to the agent** — 5 salidas tipadas que se devuelven al agente:

   | Salida | Tipo | Expresión |
   |---|---|---|
   | `total_clientes` | Number | `body('HTTP')?['total_clientes']` |
   | `download_url` | Text | `body('HTTP')?['download_url']` |
   | `csv_contenido` | Text | `body('HTTP')?['csv_contenido']` |
   | `nombre_archivo` | Text | `body('HTTP')?['nombre_archivo']` |
   | `municipios_no_reconocidos` | Text | `string(body('HTTP')?['municipios_no_reconocidos'])` |

   `municipios_no_reconocidos` se serializa explícitamente con `string(...)`
   porque **Copilot Studio no tiene un tipo de salida Object/JSON** — solo
   Text/Number/Yes-No/Date/Email/File. El agente recibe un string con forma de
   JSON (`{"San Bartolomé de Tirajana": 1200}`) y lo interpreta él mismo desde
   las Instrucciones.

Requisito de configuración: el nodo "Respond to the agent" debe tener
**Asynchronous response = Off** (en Networking) — hay un límite de 100
segundos para la respuesta síncrona completa.

### 4.2 Cómo editarlo sin perder cambios (lección aprendida esta sesión)

El editor de workflows de Copilot Studio **ha perdido cambios no guardados dos
veces** durante el desarrollo de este proyecto (ver `TASK-016` en `TODO.md`):
una vez al pulsar Escape con el selector de contenido dinámico abierto, y otra
vez las salidas de "Respond to the agent" aparecieron vacías en una revisión
posterior pese a haber pulsado Guardar. Disciplina obligatoria a partir de
ahora:

1. Hacer el cambio.
2. Pulsar **Guardar**.
3. **Recargar la página completa** (no solo cerrar el panel) y volver a abrir
   el nodo para confirmar que el cambio persiste.
4. Solo entonces, **Publicar**.

Nunca dar un cambio por guardado solo porque el botón Guardar no dio error.

## 5. Componente 3: Agente "Agente Campañas"

Mismo entorno, agent ID `fb39387b-3b2e-44ec-9faa-94bd82239b74`. Construido en
la **nueva experiencia de Copilot Studio** (Instrucciones + Tools + Skills +
Knowledge), no en la experiencia clásica basada en Topics.

### 5.1 Por qué no hay botones

La nueva experiencia **no soporta Adaptive Cards ni quick-replies** — eso es
exclusivo de la experiencia clásica con Topics (confirmado contra la
documentación oficial: [Classic vs. new agent
experience](https://learn.microsoft.com/en-us/microsoft-copilot-studio/agents-experience/classic-vs-new)).
Reconstruir el agente en la experiencia clásica solo para tener botones se
descartó por ser un cambio de arquitectura mucho más costoso que el beneficio.
Alternativa adoptada dentro de las restricciones de la nueva experiencia:
**Configuración del agente → Saludos e indicaciones** tiene un mensaje de
saludo personalizado y 5 "indicaciones sugeridas" (una por campaña) que sí se
muestran como botones pulsables en el chat, sin necesitar Adaptive Cards.

### 5.2 Tools

Una sola tool conectada: `generar_lista_campana` (el workflow de la sección 4).

### 5.3 Knowledge

`ExcelFlick.xlsx` — el mismo Excel maestro, añadido como fuente de
conocimiento **solo para que el agente pueda explicar qué información contiene
el sistema**, nunca para calcular resultados él mismo (ver instrucciones).

### 5.4 Instrucciones — estructura y por qué

Las instrucciones (editables en la pestaña "Compilar" del agente) tienen esta
estructura, en este orden, y cada bloque existe por una razón concreta
encontrada durante el desarrollo:

1. **Rol y alcance** — quién es el agente y qué NO hace (nada fuera de las 5
   campañas).
2. **Mensaje inicial** — que liste las 5 campañas en el primer mensaje, para
   que el usuario no tenga que adivinar qué puede pedir (sustituye a no poder
   usar botones de bienvenida con Adaptive Cards).
3. **Cuándo usar la herramienta** — regla explícita de "nunca calcules tú
   mismo, llama siempre a la tool", más una **tabla de mapeo literal de
   códigos de campaña** (`3 meses = 3M`, etc.). Esta tabla se añadió porque en
   una iteración anterior el modelo enviaba códigos inventados
   (`46M_PREITV`, `16M_GARANTIA`) basándose solo en la descripción del
   parámetro del workflow — la descripción del input NO fue suficiente para
   que el LLM formateara el parámetro correctamente; hizo falta reforzarlo
   también en las Instrucciones.
4. **Cuándo usar el conocimiento** — solo para explicar, nunca para generar
   resultados (evita que el agente "alucine" una lista a partir del Excel
   cargado como Knowledge en vez de llamar a la tool).
5. **Cuándo preguntar** — si no se especifica campaña, mostrar las 5 opciones
   y pedir que elija.
6. **Al mostrar el resultado de `generar_lista_campana`** — el bloque más
   largo, en este orden estricto:
   - Usar `total_clientes`/`nombre_archivo`/`download_url` literalmente, sin
     inventar.
   - Si `total_clientes` es 0, avisar y no mostrar tabla ni enlace.
   - Si hay candidatos, parsear `csv_contenido` como tabla Markdown completa
     (o primeras 20 filas + nota si son >~50 filas — decisión explícita del
     usuario de mostrar TODO el PII en el chat porque el equipo que lo usa ya
     tiene acceso al Excel original, ver `TASK-024` en `TODO.md`).
   - Después de la tabla: total, nombre de archivo, enlace, en ese orden.
   - **Si `municipios_no_reconocidos` no es `"{}"`**, añadir un aviso
     `⚠️ Nota: se han excluido N clientes...` — es informativo, no cambia el
     resultado (añadido en esta misma sesión, ver `TASK-026`).
7. **Tono**: profesional, conciso, español.

### 5.5 Trampa al editar las Instrucciones con Playwright

El campo de instrucciones es un editor de texto enriquecido (rich text). La
API de Playwright `browser_type` usa por defecto `.fill()`, que **reemplaza
TODO el contenido del campo**, no inserta en la posición del cursor. Para
añadir una frase a mitad de las instrucciones hay que: hacer clic para
posicionar el cursor, `End` + `Enter` para crear un nuevo párrafo/bullet vacío,
y solo entonces escribir ahí — nunca usar `fill()`/`browser_type` apuntando al
textbox completo cuando la intención es "añadir", no "reemplazar". Si esto
falla, el botón "Undo" del editor (no `Ctrl+Z` del sistema) revierte
correctamente el último cambio.

## 6. Hallazgo pendiente de confirmar con Flick (no es un bug de código)

Durante la prueba end-to-end de esta sesión (campaña 3M, 2026-07-22):
**224 candidatos válidos frente a 4.029 registros excluidos por municipio no
reconocido**, muchos de **San Bartolomé de Tirajana** y **Santa Lucía de
Tirajana** — municipios grandes y conocidos del sur de Gran Canaria, no
errores tipográficos.

`MUNICIPIOS_VALIDOS` (13 municipios, todos del norte/centro de la isla) es una
réplica literal de la lista que usan los Office Scripts originales — no es
algo que se haya inventado en esta migración. Dos hipótesis igual de
plausibles, y ninguna se puede resolver sin hablar con alguien de Flick que
conozca el negocio:

1. Es una exclusión de zona **deliberada** (esos municipios los atiende otro
   concesionario/zona de servicio Yamaha).
2. Es una **laguna real** en la lista heredada, y Flick lleva tiempo
   perdiendo candidatos legítimos del sur de la isla en las 5 campañas.

Ver `TASK-027` en `TODO.md`. Hasta que se resuelva, el sistema seguirá
excluyendo esos municipios exactamente igual que los scripts originales —
`municipios_no_reconocidos()` solo lo hace **visible**, no lo corrige.

## 7. Cómo replicar este sistema para otro cliente

Checklist de alto nivel, en orden:

1. **Conseguir la especificación real del negocio** — en este proyecto, un PDF
   funcional más (cuando existían) los `.osts` reales de Office Scripts. Sin
   al menos uno de los dos, cualquier campaña queda en estado "36M/46M":
   implementada pero sin validar (ver `TASK-015`).
2. **Modelar los datos de entrada** con Pydantic (`models.py`) — una fila
   normalizada, con los campos opcionales que solo use alguna campaña
   marcados como `Optional`.
3. **Extraer los filtros comunes a todas las campañas** a un módulo aparte
   (`filtros_globales.py`) — evita duplicar la misma condición de
   modelo/municipio/fecha en cada campaña, y es el punto natural para añadir
   chequeos de calidad de datos tipo `municipios_no_reconocidos()`.
4. **Implementar cada campaña como una función pura** `list[Registro] ->
   list[Registro]`, con tests que fijen el comportamiento contra casos reales
   conocidos (sanity check con el script original si existe).
5. **Azure Function HTTP-trigger** que orqueste: leer Excel → filtrar →
   generar CSV (para mostrar) + Excel (para descargar) → subir a Blob Storage
   → devolver JSON.
6. **Blob Storage con SAS de expiración corta** para el archivo descargable —
   evita el límite de tamaño de respuesta de los custom connectors/workflows
   de Copilot Studio (ver `DEC-003`).
7. **Workflow nativo de Copilot Studio** (`When an agent calls the flow` →
   conector de origen de datos → HTTP a la Function → `Respond to the agent`)
   — más simple que un flujo de Power Automate clásico si el agente ya vive en
   la nueva experiencia. Recordar: sin tipo Object, serializar dicts/listas
   con `string(...)` si hace falta devolverlos.
8. **Agente con Instrucciones explícitas**, no solo descripciones de
   parámetros — el LLM necesita el mapeo de valores literal repetido en las
   Instrucciones si el usuario habla en lenguaje natural y la tool espera
   códigos exactos.
9. **Decisiones de negocio a confirmar explícitamente con el cliente antes de
   producción**: qué PII es aceptable mostrar en el chat, si hay listas
   cerradas (municipios, códigos, modelos) que puedan quedar desactualizadas,
   y qué campañas tienen script de referencia real vs. solo documentación.

## 8. Referencias

- Spec de diseño original: `../docs/superpowers/specs/2026-07-21-motor-segmentacion-azure-function-design.md`
- Plan de implementación (15 tasks): `../docs/superpowers/plans/2026-07-21-segmentacion-campanas-azure-function.md`
- Historial completo de decisiones, bugs encontrados/corregidos, e incidentes: `../TODO.md`
- README de uso rápido de la Function: `README.md`
