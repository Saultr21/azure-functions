# Flick Chatbot — Motor de segmentación con Azure Function

**Fecha:** 2026-07-21
**Estado:** Pendiente de revisión final del usuario
**Cliente:** Flick (marca Yamaha)

## 1. Contexto

El chatbot de Flick en Microsoft Copilot Studio automatiza la generación de listados de
clientes para 5 campañas de marketing posventa. La implementación actual usa:

Copilot Studio → Power Automate → Office Script (TypeScript) sobre un Excel maestro en
OneDrive/SharePoint → CSV en Base64 devuelto al chat.

### Problemas detectados en la arquitectura actual

1. **Límites de Office Scripts**: timeout de 120s en operaciones síncronas de Power
   Automate, 5MB por request/response, 5M celdas por rango. Con ~15.000 filas hoy y
   crecimiento continuo del histórico del taller, el margen se reduce con el tiempo.
2. **Lógica de filtrado duplicada** en 5 Office Scripts independientes — cada campaña
   reimplementa los filtros globales y su criterio específico.
3. **Límite de 500KB en la respuesta de los custom connectors de Copilot Studio** — el
   CSV en Base64 puede chocar con este límite según crezca el volumen de una campaña.
4. **Excel como base de datos** es frágil: un renombrado de columna rompe todos los
   scripts (ya documentado como riesgo conocido).

### Discrepancias encontradas entre el PDF y el código real (`.osts`)

Durante el diseño se localizaron los Office Scripts reales de 3 de las 5 campañas
(`Flick/office-scripts-actuales/FiltrarSinVisita3Meses(csv).osts`,
`Fecha24MesesSinVisita(CSV).osts`, `16 m garantía ±30d.osts`) y se compararon con el
PDF y con el Excel maestro real (`ExcelFlick.xlsx`, 31.322 filas, no versionado por
confidencialidad — ver `.gitignore`). Se encontraron diferencias de negocio no triviales:

- **Campaña 16M**: el PDF describe el criterio como "Fecha.exp.garantia dentro de
  ±30 días de hoy". El script real filtra por **Fecha.matriculación en una ventana de
  15-16 meses** y excluye a quien ya tiene `Inicio.garant.extend` relleno (ya contrató
  la garantía extendida). Se verificó en el Excel real que `Fecha.exp.garantia` =
  `Fecha.matriculación` + 24 meses de forma consistente (garantía estándar de 2 años).
  Esto confirma que el criterio real **no es un error**: es una campaña de venta
  proactiva de garantía extendida ~8 meses antes de que expire la garantía estándar,
  con margen de decisión para el cliente — más coherente de negocio que un aviso a
  ±30 días del vencimiento. **Se implementa el criterio del script real.** El PDF debe
  corregirse aparte para reflejar esto.
- **Campaña 3M**: el script real añade un criterio no documentado en el PDF —
  excluye vehículos con `Kilometraje` (último servicio) ≥ 200 km. Solo se dirige a
  vehículos de uso muy reciente/bajo. Se implementa tal cual está en producción.
- **Campañas 36M y 46M/Pre-ITV**: no existe script real disponible para estas dos.
  Se implementan desde cero siguiendo únicamente la descripción del PDF (§5 del PDF
  original). Dado que ya se demostró que el PDF puede estar desactualizado o
  incompleto respecto al criterio real (caso 16M), **estas dos campañas requieren
  validación manual contra un resultado de referencia antes de sustituir el proceso
  actual en producción** (ver §8 Testing).

## 2. Objetivo del cambio

Sustituir Power Automate + Office Scripts como motor de procesamiento por una **Azure
Function en Python**, manteniendo Copilot Studio como capa puramente conversacional y
el Excel maestro como fuente de datos (sin migrar a otra base de datos en esta fase).

## 3. Restricción de acceso (decisiva para el diseño)

El desarrollador tiene acceso a la suscripción Azure de CognitiaTech y al entorno
Power Platform de Flick (Copilot Studio, Power Automate), pero **no** tiene acceso al
Entra ID / Azure AD del tenant de Flick. Esto descarta cualquier diseño que requiera
un app registration en el tenant de Flick (ni para OAuth del custom connector, ni para
acceso directo vía Microsoft Graph API al OneDrive de Flick).

**Consecuencia de diseño:** Power Automate se mantiene en el flujo, no como motor de
procesamiento, sino como **puente de datos autenticado** — es el único componente que
ya tiene una conexión válida al OneDrive/SharePoint de Flick.

## 4. Arquitectura

```
Usuario → Copilot Studio (quick reply de campaña)
        → Power Automate (tenant Flick, conexión OneDrive ya existente)
              1. Get file content del Excel maestro (binario)
              2. HTTP POST a la Azure Function
                 URL: /api/segmentar_campana?campana=<id>&code=<function-key>
                 Content-Type: application/octet-stream
                 Body: bytes crudos del .xlsx (sin Base64 — mismo patrón que ExcelFlick)
        → Azure Function (Python, suscripción CognitiaTech)
              1. Valida "campana" contra whitelist cerrada (Enum) — 400 si no coincide
              2. Carga el Excel (openpyxl) directamente desde el body binario
              3. Aplica filtros globales (modelo, municipio, fecha matriculación,
                 códigos excluidos) + criterio específico de la campaña
              4. Normaliza texto (NFD, minúsculas) antes de comparar
              5. Deduplica por matrícula (conserva la visita más reciente)
              6. Ordena por fecha de servicio
              7. Genera el CSV (mismo formato de columnas que la salida actual)
              8. Sube el CSV a Blob Storage; genera SAS de lectura de 24h
              9. Devuelve JSON { "total_clientes": N, "download_url": "...", "logs": [...] }
        → Power Automate recibe la respuesta y la pasa a Copilot Studio
        → Copilot Studio muestra el resumen + enlace de descarga al usuario
```

Se usa binario crudo (`application/octet-stream`) en vez de Base64 dentro de un JSON,
siguiendo la convención ya establecida en `ExcelFlick/function_app.py` (repo
`Saultr21/azure-functions`) — evita ~33% de overhead de codificación y es consistente
con el resto de funciones del repo.

### Por qué esta arquitectura y no las alternativas descartadas

- **Copilot Studio → Function directo (sin Power Automate)**: descartado porque
  requeriría un app registration Entra ID en el tenant de Flick para el custom
  connector, que el desarrollador no puede crear (Restricción §3).
- **Function accede a OneDrive vía Graph API directamente**: mismo problema — necesita
  permisos Files.Read.All/Sites.Read.All en el tenant de Flick.
- **Migrar el Excel a Azure SQL/Dataverse**: descartado para esta fase por alcance;
  válido como mejora futura si el volumen de datos lo justifica.

## 5. Componentes

| Componente | Responsabilidad | Notas |
|---|---|---|
| Copilot Studio | UI conversacional: quick replies, mensaje de espera, presentación del resultado | Sin lógica de negocio |
| Power Automate | Puente de datos: lee el Excel de Flick, llama a la Function, entrega la respuesta | Flujo mínimo, sin lógica de filtrado |
| Azure Function (`SegmentacionCampanas/`) | Motor único de filtrado config-driven, generación de CSV, subida a Blob | Config de campaña centralizada (no 5 scripts) |
| Blob Storage | Almacenamiento temporal del CSV | SAS 24h + lifecycle policy de borrado a 7 días |

### Estructura del código de la Function (orientativa)

Sigue la convención del repo (una carpeta por función), agrupada bajo `Flick/`
junto con el resto de artefactos de este proyecto (specs, scripts actuales):

```
Flick/SegmentacionCampanas/
  function_app.py       # entry point HTTP trigger (@app.route)
  campaigns.py           # config declarativa de las 5 campañas (Pydantic models)
  filters.py             # filtros globales + motor de aplicación de criterios
  excel_reader.py         # parseo del Excel (openpyxl), parseo de fechas (3 formatos)
  csv_writer.py           # generación de CSV + subida a Blob + SAS
  models.py              # Pydantic: request/response schemas
  host.json
  requirements.txt
  README.md
```

## 6. Seguridad (Gate 1 y 2 de ssdlc)

### Datos sensibles

El Excel y el CSV resultante contienen PII de clientes de Flick: teléfono, email,
dirección, matrícula. Estos datos cruzan de el tenant de Flick a la suscripción Azure
de CognitiaTech para su procesamiento — se asume cobertura contractual existente como
encargado del tratamiento; si no existe, debe confirmarse con Flick antes de desplegar.

### Amenazas principales (STRIDE) y mitigación

1. **Fuga de info por function key comprometida** → cualquiera podría solicitar
   listados de clientes de cualquier campaña.
   Mitigación: function-level key (no host key), solo HTTPS, whitelist cerrada de
   nombres de campaña (Enum, no string libre).
2. **Fuga de info vía el link de descarga** si el SAS URL se reenvía o se filtra.
   Mitigación: SAS de solo lectura, scoped a un único blob, expiración de 24h.
3. **Tampering / DoS** con payloads manipulados o excesivos contra el endpoint.
   Mitigación: validación de esquema de entrada (Pydantic), límite de tamaño de
   payload, Consumption Plan con límites de concurrencia, errores genéricos sin
   detalles internos (sin paths, sin schema de datos) en la respuesta al cliente.

### Controles no negociables

- Ningún log contiene valores de PII (teléfono, email, dirección) — solo nombre de
  campaña y contadores.
- Lifecycle policy en Blob Storage: borrado automático de blobs a los 7 días,
  independiente de la expiración del SAS.
- `pip-audit` antes de cada merge (Gate 4 ssdlc).
- Secrets (function key, connection string de Blob) vía variables de entorno /
  Azure Key Vault — nunca en código ni en el repositorio.

## 7. Manejo de errores

| Escenario | Comportamiento |
|---|---|
| Excel ilegible / hoja "Hoja1" no encontrada / columna requerida ausente | Function devuelve error estructurado (código + mensaje genérico); Power Automate lo traduce a un mensaje claro en el chat; detalle completo solo en Application Insights |
| Campaña no reconocida | Rechazo inmediato (400), no se procesa nada |
| 0 resultados tras filtrado | No es un error: el chat informa "0 clientes encontrados para esta campaña", sin generar CSV ni blob |
| Timeout / fallo de Power Automate al leer el Excel | Se mantiene el manejo de error nativo de Power Automate (reintentos configurables) |

## 8. Testing

- Unit tests del motor de filtrado por campaña: fechas nulas, los 3 formatos de fecha
  documentados (serie Excel, DD/MM/YYYY, valores nulos "--/--/--"), deduplicación por
  matrícula, normalización de texto con acentos (ej. "Gáldar" vs "galdar").
- Test de integración con un Excel de muestra (fixture) para cada una de las 5
  campañas, comparando el CSV de salida contra el esperado.
- **Para 3M, 24M y 16M** (con script real de referencia): el test de integración
  compara el CSV generado por la Function contra el CSV que produce hoy el Office
  Script original sobre el mismo Excel — deben coincidir fila a fila.
- **Para 36M y 46M/Pre-ITV** (sin script real, implementadas desde el PDF): antes de
  sustituir el proceso en producción, ejecutar la Function sobre el Excel real y
  revisar manualmente una muestra de los resultados con alguien de Flick que conozca
  el negocio, para confirmar que el criterio interpretado del PDF es el correcto —
  el mismo tipo de discrepancia encontrada en 16M podría repetirse aquí.
- `pip-audit` antes de cerrar cualquier PR.

## 9. Fuera de alcance (esta fase)

- Migración del Excel maestro a Azure SQL/Dataverse.
- Autenticación OAuth/Entra ID entre Flick y la Function (bloqueada por la restricción
  de acceso documentada en §3; revisar si en el futuro Flick puede dar de alta el app
  registration).
- Añadir nuevas campañas más allá de las 5 actuales.
- **`FiltrarMantenimientoPorHito` + `CalcularMediasKilometraje`**: scripts ya
  existentes en el repo que calculan, por modelo, la media histórica de meses para
  alcanzar cada hito de kilometraje de mantenimiento, y filtran clientes que se
  acercan a su próximo hito según su ritmo de uso real. Es una herramienta con valor
  real (cubre un caso — mantenimiento por uso — que ninguna de las 5 campañas
  cubre), pero su interfaz (parámetros `modeloObjetivo` + `hitoActual`, no una
  selección fija) no encaja en el patrón de quick-reply de un solo botón del chatbot
  actual. Se recomienda migrarla en una fase posterior, con su propia spec, evaluando
  si necesita una interacción de chatbot distinta (ej. el usuario elige el modelo) o
  si debe ejecutarse en batch para todos los modelos automáticamente.

## 10. Siguiente paso

Invocar la skill `writing-plans` para descomponer este diseño en un plan de
implementación paso a paso.
