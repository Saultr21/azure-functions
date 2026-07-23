# TODO — Flick: Motor de Segmentación con Azure Function

> Last updated: 2026-07-23
> Current phase: deployment (agente de Copilot Studio conectado, evaluado formalmente y probado end-to-end; avisos de municipios ya deterministas; agente replicado y verificado también en el tenant de Cognitia; pendiente solo validación manual de negocio y confirmar la zona de servicio real)
> Overall progress: 15/15 tasks del plan + desplegado en Azure + agente evaluado (pestaña Evaluar) y con el aviso de municipios corregido para ser fiable + exportado y verificado en el tenant de Cognitia (entorno "Cognitia DEV")

## Completed

- [x] `TASK-016` — **Conectar Power Automate → Azure Function (hecho vía Copilot Studio, no Power Automate clásico)**
  - Entorno real de Flick: Copilot Studio "AgenteFlick" (tenant `grupoflick.onmicrosoft.com`), agente **"Agente Campañas"**, workflow tool **`generar_lista_campana`** (nueva experiencia de Copilot Studio, no Power Automate clásico — el agente ya existía construido así).
  - Flujo: `When an agent calls the flow` (input `campana`, texto) → **OneDrive "Obtener contenido de archivo"** (conexión `sistemas3@grupoflick.onmicrosoft.com`, archivo `/ExcelFlick/ExcelFlick.xlsx`) → **HTTP POST** a `https://func-flick-segmentacion.azurewebsites.net/api/segmentar_campana` (header `Content-Type: application/octet-stream`, query `campana` + `code`=function key, body=contenido del archivo) → **Respond to the agent** (`total_clientes`, `download_url`).
  - Probado end-to-end en el chat de vista previa: petición "16 meses de garantía" → 14 candidatos, CSV `FiltradoCampana16M_2026-07-22.csv`, enlace SAS de descarga — **coincide exactamente** con el sanity check original de TASK-001..014 (16M=14 candidatos).
  - Bugs encontrados y corregidos durante la integración:
    - La descripción del input `campana` decía usar códigos `46M_PREITV`/`16M_GARANTIA` (invención mía, sin verificar el código) — los códigos reales en `models.py` son `3M/24M/36M/46M/16M`. Corregido en la descripción del input y reforzado con mapeo explícito en las Instrucciones del agente (el modelo no seguía fielmente solo la descripción del parámetro).
    - El nodo "Respond to the agent" se quedó sin las salidas (`total_clientes`/`download_url`) configuradas al menos dos veces durante la sesión — el editor de Copilot Studio parece perder cambios no confirmados si se navega fuera del panel antes de que el autoguardado confirme. Mitigación: tras configurar salidas, verificar con recarga de página que persisten antes de seguir.
  - Añadido también (fuera del alcance original de TASK-016, a petición del usuario): mensaje de saludo personalizado y 5 "indicaciones sugeridas" (una por campaña) en Configuración del agente → Saludos e indicaciones, ya que la nueva experiencia de Copilot Studio no soporta Adaptive Cards/botones (eso es exclusivo de la experiencia clásica con Topics, según [Classic vs. new agent experience](https://learn.microsoft.com/en-us/microsoft-copilot-studio/agents-experience/classic-vs-new)).
  - **Incidente de seguridad menor**: la function key quedó expuesta en texto plano en mi contexto una vez, al inspeccionar el detalle de una ejecución fallida del flujo (el panel "Detalles de la ejecución" no enmascara valores de query params). Usuario decidió no rotarla de inmediato (entorno de pruebas). Pendiente rotarla antes de pasar a producción real (ver TASK-023).

- [x] `TASK-024` — **Mostrar resultados en el chat + enlace de descarga que abre en vez de forzar descarga**
  - `blob_storage.py`: el blob se sube ahora con `ContentSettings(content_type="text/plain; charset=utf-8", content_disposition='inline; filename="..."')` en vez de `content_settings=None` — antes el enlace SAS forzaba una descarga "rara" (sin tipo definido); ahora abre el CSV como texto plano en una pestaña del navegador.
  - `function_app.py`: la respuesta 200 ahora incluye también `csv_contenido` (el CSV completo) y `nombre_archivo`, además de `total_clientes`/`download_url`. Antes solo devolvía conteo y link.
  - Redesplegado en Azure (`func azure functionapp publish func-flick-segmentacion`) — 63 tests en verde antes del despliegue.
  - Workflow `generar_lista_campana` en Copilot Studio: añadidas las salidas `csv_contenido` y `nombre_archivo` en "Respond to the agent" (antes solo `total_clientes`/`download_url`).
  - Instrucciones del agente actualizadas: ahora parsea `csv_contenido` y lo muestra como tabla Markdown en el chat (todas las filas si son pocas, primeras 20 + nota si son muchas), seguido siempre de total/nombre de archivo/enlace.
  - **Decisión de negocio del usuario**: el CSV contiene PII (teléfono, email, dirección) y antes se evitaba deliberadamente su log (ver docstring de `blob_storage.py`); el usuario decidió explícitamente que mostrar el contenido completo en el chat es aceptable porque el equipo que usa el chat ya tiene acceso al Excel/CSV original. Verificado end-to-end con datos reales (campaña 16M, 1 candidato en Moya) — la tabla se renderiza correctamente y el agente puede incluso responder preguntas de seguimiento filtrando sobre los datos ya mostrados.

- [x] `TASK-025` — **Archivo descargable en Excel (.xlsx) en vez de CSV**
  - Nuevo `excel_writer.py` (`generar_excel`, `nombre_archivo_excel`) — reutiliza `cabeceras_para`/`valor_campo` de `csv_writer.py` (antes privados `_cabeceras_para`/`_valor_campo`, ahora públicos y compartidos entre ambos writers). A diferencia del CSV, los números se guardan como celdas numéricas reales (no texto), y no hace falta escapar `;`.
  - `ResultadoCampana` (motor.py) ahora tiene tanto `csv_contenido` (texto, solo para la tabla del chat) como `excel_contenido` (bytes, para el archivo descargable) y `nombre_archivo` termina en `.xlsx`.
  - `blob_storage.py`: `subir_csv_y_generar_link` → renombrada a `subir_excel_y_generar_link`, recibe bytes en vez de texto, sube con `content_type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` y `content_disposition=attachment` (a diferencia del texto plano anterior, un .xlsx no se puede previsualizar en el navegador, así que se ofrece como descarga directa con el nombre correcto).
  - `csv_writer.py`: eliminada `nombre_archivo_csv` (quedó sin uso al pasar la descarga a Excel).
  - El JSON de respuesta de la Function no cambió de forma (mismos campos: `total_clientes`, `download_url`, `nombre_archivo`, `csv_contenido`) — **no hizo falta tocar el flujo de Copilot Studio**, solo redesplegar la Function App.
  - 65 tests en verde (2 nuevos en `test_excel_writer.py`) antes del redespliegue a Azure.
  - **Nota (falso positivo investigado)**: tras el despliegue, un usuario reportó que el enlace "descargaba algo raro, no un Excel". Verificado con `curl` contra la URL SAS exacta del chat: headers (`Content-Type`, `Content-Disposition`) y contenido correctos, `file` confirma "Microsoft Excel 2007+" válido. El problema era que Chrome guardaba la descarga con un nombre GUID en vez del nombre real del archivo (sin extensión visible) — comportamiento del navegador, no un bug de la Function/Blob Storage. Si se repite con otro usuario, comprobar primero si el navegador está renombrando la descarga antes de sospechar del backend.

- [x] `TASK-026` — **Visibilidad de municipios no reconocidos**
  - Origen: el usuario cuestionó (con razón) que `MUNICIPIOS_VALIDOS` sea una lista cerrada en código — si viene un cliente de un municipio nuevo/no listado, se descarta silenciosamente de las 5 campañas sin ningún aviso.
  - Decisión del usuario: mantener la lista en código (no moverla a config externa — cambia poquísimo, y así queda protegida por tests), pero **sí** añadir visibilidad de cuántos registros se pierden por esto.
  - Nueva `municipios_no_reconocidos()` en `filtros_globales.py`: cuenta, solo entre registros con un **modelo Yamaha válido** (para no contar ruido de gente que ya se descartaría por modelo), cuántos tienen un municipio fuera de `MUNICIPIOS_VALIDOS`, agrupado por el texto tal cual aparece en el Excel.
  - `ResultadoCampana` añade el campo `municipios_no_reconocidos: dict[str, int]`; `function_app.py` lo incluye en la respuesta JSON (éxito y 0 resultados) y lo loguea como warning en Application Insights cuando no está vacío.
  - No cambia qué se filtra — es puramente informativo. 69 tests en verde, redesplegado en Azure.
  - **Extensión (mismo día): surfacing en el chat del agente.** Añadida una nueva salida `municipios_no_reconocidos` (Text) en el nodo "Respond to the agent" del workflow `generar_lista_campana`, con la expresión `@{string(body('HTTP')?['municipios_no_reconocidos'])}` (se serializa a JSON string porque Copilot Studio no tiene tipo de salida Object). Instrucciones del agente actualizadas para mostrar, tras el enlace de descarga, un aviso `⚠️ Nota: se han excluido N clientes...` cuando el diccionario no está vacío. Verificado end-to-end en el chat de vista previa.
  - **Hallazgo relevante encontrado durante la prueba end-to-end (campaña 3M, 2026-07-22): 4.029 clientes excluidos por municipio no reconocido, frente a solo 224 candidatos válidos.** Los municipios no reconocidos más frecuentes incluyen **San Bartolomé de Tirajana** y **Santa Lucía de Tirajana** — municipios grandes y conocidos de Gran Canaria, no errores tipográficos ni casos raros. Esto sugiere que `MUNICIPIOS_VALIDOS` (13 municipios, todos del norte/centro de la isla) podría estar excluyendo por diseño zonas de servicio completas del sur (posiblemente cubiertas por otro concesionario/zona), o podría ser una laguna real de la lista heredada de los Office Scripts. Requiere confirmación de negocio — ver `TASK-027`.

- [x] `TASK-021` — **Desplegado en Azure real (suscripción CognitiaTech) y probado en producción**
  - Recursos creados en `flick-segmentacion-rg` (Sweden Central):
    - Storage Account `stflicksegcampanas` (HTTPS-only, TLS 1.2 mínimo, contenedor
      privado `csv-campanas` con lifecycle policy de borrado a 7 días)
    - Function App `func-flick-segmentacion` (Linux, Consumption, Python 3.12,
      HTTPS-only forzado, Application Insights auto-creado)
  - Actualizada de Python 3.10 a 3.12 el mismo día (aviso de EOL de runtime a
    31/10/2026, quedaban ~3 meses) — redeploy verificado, endpoint sigue
    funcionando igual tras el cambio. Pendiente de baja prioridad: migrar de
    Consumo Linux a Flex Consumption (EOL 30/09/2028, sin urgencia).
  - Prueba end-to-end real contra `https://func-flick-segmentacion.azurewebsites.net/api/segmentar_campana`
    con un Excel sintético (sin PII real): 200 OK con CSV correcto (campaña 24M),
    400 con `campana_requerida`/`campana_desconocida`, 200 con `download_url: null`
    en 0 resultados (16M) — los 4 casos coinciden exactamente con los tests unitarios.
  - Blob de prueba borrado tras la validación.
  - Nota: aparece una función fantasma `SegmentacionCampanasFlick` en el listado
    (`az functionapp function list`) — es un artefacto del placeholder que Azure
    crea al aprovisionar Function Apps en Linux Consumption, no corresponde a
    código real (confirmado: `function_app.py` solo define `segmentar_campana`).
    Requiere `code` válido para responder (401 sin key) y no tiene ruta real
    detrás; inofensivo pero cosmético — desaparecerá en un futuro redeploy.

- [x] `TASK-001` a `TASK-014` — Las 15 tasks del plan de implementación
  - Spec: `docs/superpowers/specs/2026-07-21-motor-segmentacion-azure-function-design.md`
  - Plan: `docs/superpowers/plans/2026-07-21-segmentacion-campanas-azure-function.md`
  - Resumen: Azure Function en Python (`SegmentacionCampanas/`) que sustituye a los
    Office Scripts de las 5 campañas del chatbot (3M, 24M, 36M, 46M/Pre-ITV, 16M
    garantía). 63 tests, todos en verde. Sanity check ejecutado contra el Excel
    real (31.300 filas): 3M=223, 24M=545, 16M=14, 36M=373, 46M=257 candidatos —
    magnitudes razonables, sin errores.
  - Fixes encontrados durante la implementación (documentados en el plan):
    - `restar_meses_estilo_js` en `utils.py` sustituye a `dateutil.relativedelta`
      (que clampeaba fechas inválidas en vez de desbordar como JS `Date.setMonth`).
    - El filtro de código de servicio excluido se aplica DESPUÉS de deduplicar
      (no antes) — bug real encontrado comparando contra el `.osts` de 24M.
    - Formato numérico del CSV corregido (evita sufijo `.0` en kilometrajes enteros).

- [x] `TASK-030` — **Evaluación formal del agente (pestaña Evaluar) + pruebas de casos límite**
  - Hecho el 2026-07-23 siguiendo el checklist oficial de Microsoft ([evaluation-checklist](https://learn.microsoft.com/en-us/microsoft-copilot-studio/guidance/evaluation-checklist)).
  - Conjunto "Núcleo - 5 campañas (auto)": 10 conversaciones multi-turno auto-generadas (las 5 campañas × 2 redacciones, en inglés). Método "Calidad general" (juez LLM). Resultado: los primeros casos de las 5 campañas salieron **Aprobado** (la ejecución se quedó lenta/atascada hacia 5/10, pero ya cubría las 5 campañas; los 5 restantes eran duplicados de intención). Herramienta `generar_lista_campana` invocada en todos, respuesta en español pese a preguntar en inglés, tabla + total + archivo + enlace + manejo correcto del multi-turno (incluida la pregunta "¿y si no hay candidatos?").
  - Casos límite probados a mano en vista previa (que el auto-set no cubría):
    - Fuera de alcance ("¿qué tiempo hace hoy?") → **correcto**: rechaza y reconduce a las 5 campañas.
    - Lenguaje natural sin código ("clientes que llevan más de dos años sin pasar por el taller") → **correcto**: mapea a 24M, llama a la herramienta, 546 candidatos.
  - Único defecto encontrado: el aviso de municipios no reconocidos (ver `TASK-029`, ya resuelto).

- [x] `TASK-029` — **Aviso de municipios no reconocidos fiable (conteo calculado en Python, no por el LLM)**
  - Origen: evaluación + pruebas manuales de `TASK-030` (2026-07-23).
  - Síntoma: sobre el MISMO dato (fijo para un Excel dado), el agente mostraba el aviso de 4 formas distintas: "4.029", "906", "5.134" y sin número. Causa: las Instrucciones pedían al LLM sumar los valores de un JSON, y los LLM no suman de forma fiable.
  - Fix aplicado: nueva `resumen_municipios_no_reconocidos()` en `filtros_globales.py` que devuelve `(total, resumen)` ya calculados en Python (resumen = top-10 municipios `nombre: N; ...` + "y N municipio(s) más"). `ResultadoCampana` y la respuesta JSON de la Function exponen `municipios_no_reconocidos_total` y `municipios_no_reconocidos_resumen`. En el workflow, la salida antigua `municipios_no_reconocidos` (JSON) se reemplazó por `municipios_no_reconocidos_resumen` (Text) y se añadió `municipios_no_reconocidos_total` (Number). La Instrucción del agente ahora repite ambos valores VERBATIM (nunca los calcula).
  - Verificado end-to-end: dos ejecuciones de la campaña 3M devuelven el MISMO aviso determinista ("se han excluido 4080 clientes... (vacío): 906; San Bartolomé De Tirajana: 219; ..."). 72 tests en verde. Function redesplegada; workflow y agente republicados.
  - Efecto colateral útil para `TASK-027`: el detalle deja ver que hay ~206 variantes de municipio no reconocidas, muchas por mayúsculas/acentos del mismo pueblo (San Bartolomé/Santa Lucía de Tirajana aparecen 2-3 veces cada una) además de ruido de datos ("(vacío)": 906, "Taco": 117).

- [x] `TASK-031` — **Exportar el agente al tenant de Cognitia (entorno "Cognitia DEV")**
  - Origen: petición explícita del usuario para llevar el agente al tenant de CognitiaTech, reutilizando la misma Azure Function de Flick; el Excel maestro se subió a un sitio SharePoint de Cognitia ("Flickagente") en vez de a un OneDrive personal.
  - Lado Flick: creada una solución no administrada en Copilot Studio con el agente "Agente Campañas" y sus dependencias (workflow `generar_lista_campana`, conexiones), exportada como `.zip`.
  - Lado Cognitia: se detectó y eliminó (decisión del usuario) una solución "Agente flick" preexistente de 6 meses de antigüedad antes de importar, para evitar duplicados. Se creó un entorno dedicado **"Cognitia DEV"** (en vez de usar el entorno Default del tenant) para esta importación, siguiendo la práctica recomendada de no mezclar trabajo de desarrollo con el entorno compartido.
  - Tras importar, la conexión del workflow al Excel quedó rota porque apuntaba al OneDrive de Flick (`sistemas3@grupoflick.onmicrosoft.com`), inexistente en Cognitia. Además, el Excel real vivía en un **sitio SharePoint** ("Flickagente" → Documentos compartidos → General), no en un OneDrive personal — el conector OneDrive no puede navegar bibliotecas de sitios SharePoint. Fix: se cambió el nodo "Obtener contenido de archivo" del workflow de conector OneDrive a conector **SharePoint**, apuntando a `https://cognitiatech.sharepoint.com/sites/Flickagente` → Documentos compartidos → General → `ExcelFlick.xlsx`.
  - El Knowledge source del agente (`ExcelFlick.xlsx`) tenía el mismo problema (apuntaba a la URL de SharePoint de Flick) — se quitó y se volvió a añadir con el conector SharePoint de Cognitia, misma ruta que el workflow.
  - Verificado end-to-end en vista previa dentro de Cognitia DEV: campaña 3M → 225 candidatos, tabla correcta, archivo `FiltradoCampana3M_2026-07-23.xlsx`, enlace de descarga apuntando a la misma Function/Blob Storage de Flick (`stflicksegcampanas.blob.core.windows.net`), y aviso de municipios no reconocidos con el total determinista **4080** (mismo valor que en Flick tras el fix de `TASK-029`) — confirma que ambos tenants comparten backend y que el fix de determinismo se replicó correctamente.
  - Agente guardado y publicado con éxito en Cognitia DEV ("Agent published successfully").

## Discovered / Backlog

- [ ] `TASK-015` — **Validación manual contra producción (BLOQUEA el paso a producción)**
  - Origen: spec §8, plan Task 15
  - Prioridad: alta
  - Qué falta: generar el CSV con el Office Script real para 3M/24M/16M sobre el
    Excel maestro actual y comparar fila a fila contra el CSV de la nueva Function
    (deben coincidir exactamente). Para 36M y 46M/Pre-ITV (sin script real de
    referencia), revisar manualmente una muestra de resultados con alguien de
    Flick que conozca el negocio — el mismo tipo de discrepancia encontrada en
    16M (el PDF describía mal el criterio real) podría repetirse aquí.
  - Esto requiere acceso al entorno de Power Automate/Copilot Studio de Flick,
    que un agente no puede ejecutar de forma autónoma.

- [ ] `TASK-027` — **Confirmar con Flick si excluir San Bartolomé/Santa Lucía de Tirajana (zona sur) es intencional**
  - Origen: hallazgo durante la prueba end-to-end de TASK-026 (ver arriba) — 4.029 registros excluidos de la campaña 3M solo en la ejecución de prueba, muchos de municipios grandes del sur de Gran Canaria que no están en `MUNICIPIOS_VALIDOS`.
  - Prioridad: alta — podría significar que Flick está perdiendo un volumen grande de candidatos legítimos en las 5 campañas, o podría ser una exclusión de zona deliberada (p. ej. esos municipios los atiende otro concesionario Yamaha). Relacionado con `TASK-015` (validación manual de negocio).
  - Qué falta: preguntar a alguien de Flick que conozca el negocio si la lista de 13 municipios (`arucas, firgas, galdar, ingenio, moya, las palmas, santa brigida, guia, telde, teror, valleseco, valsequillo, vega de san mateo`) es la zona de servicio completa o si faltan municipios por añadir a `MUNICIPIOS_VALIDOS` en `filtros_globales.py`.

- [ ] `TASK-022` — Migrar de Consumo Linux a Flex Consumption
  - Origen: aviso de Azure Portal (retirada de Consumo Linux, 30/09/2028)
  - Prioridad: baja
  - Notas: sin urgencia (quedan más de 2 años). Flex Consumption ofrece
    arranque en frío más rápido y redes privadas — evaluar cuando el proyecto
    esté validado y estable en producción.

- [ ] `TASK-018` — Refactor: extraer un helper genérico "N meses sin visita"
  - Origen: code review de Task 10
  - Prioridad: baja (revisar después de TASK-015)
  - Notas: `campana_24m.py`, `campana_36m.py` y `campana_46m_preitv.py` son casi
    idénticos salvo el número de meses. Se dejó la duplicación deliberadamente
    (YAGNI) porque 36M/46M aún no están validados y podrían necesitar reglas
    propias tras TASK-015 — abstraer antes sería prematuro.

- [ ] `TASK-019` — Migrar `FiltrarMantenimientoPorHito` / `CalcularMediasKilometraje`
  - Origen: spec §9
  - Prioridad: baja
  - Notas: herramienta de mantenimiento por uso real (km), separada de las 5
    campañas del chatbot. Necesita su propia spec — no encaja en el patrón de
    quick-reply de un solo botón.

- [ ] `TASK-020` — Cosmético: acento faltante en el commit `47fce8b`
  - Origen: code review de Task 5
  - Prioridad: muy baja
  - Notas: el mensaje dice "deteccion" en vez de "detección". Ya está pusheado
    a GitHub — no vale la pena reescribir historial por esto.

## Architecture Decisions

- `DEC-001`: Power Automate se mantiene como puente de datos autenticado (lee el
  Excel de Flick y llama a la Function), no como motor de procesamiento — el
  desarrollador no tiene acceso a Entra ID del tenant de Flick para un custom
  connector directo. (2026-07-21)
- `DEC-002`: Autenticación Function↔Power Automate vía function key simple, no
  OAuth/Entra ID — mismo motivo que DEC-001. (2026-07-21)
- `DEC-003`: El CSV se entrega como link de descarga desde Blob Storage (SAS 24h),
  no inline en Base64 — evita el límite de 500KB de los custom connectors de
  Copilot Studio. (2026-07-21)
- `DEC-004`: Para 16M, se implementa el criterio del script real (ventana de
  matriculación 15-16 meses) en vez del criterio descrito en el PDF (±30 días de
  expiración de garantía) — verificado contra el Excel real que
  `Fecha.exp.garantia` = `Fecha.matriculación` + 24 meses, confirmando que el
  script real es una campaña de venta proactiva de garantía extendida, no un
  aviso de vencimiento. (2026-07-21)
- `DEC-005`: El puente hacia la Function no se implementó como flujo de Power
  Automate clásico sino como **workflow tool nativo de Copilot Studio** (nueva
  experiencia, `When an agent calls the flow` + `Respond to the agent`) — el
  agente "Agente Campañas" ya existía construido en esa experiencia, y las
  herramientas de este tipo se ejecutan directamente desde el agente sin pasar
  por Power Automate como capa intermedia. DEC-001/002/003 siguen aplicando
  igual (function key simple, CSV vía link de Blob Storage). (2026-07-22)

- [x] `TASK-028` — **Documento de arquitectura y replicación (`SegmentacionCampanas/ARQUITECTURA.md`)**
  - Origen: petición explícita del usuario para poder mantener y replicar el sistema completo (Function + workflow + agente) en otro cliente en el futuro.
  - Cubre: diagrama de extremo a extremo, lógica de negocio de las 5 campañas y sus filtros/dedup, infraestructura Azure, configuración exacta del workflow y del agente en Copilot Studio (con las trampas encontradas: pérdida de cambios no guardados, `fill()` de Playwright reemplazando el editor rich-text en vez de insertar), el hallazgo de `TASK-027`, y un checklist paso a paso para replicar el patrón con otro cliente.

## Notes

- El repo es `Saultr21/azure-functions` (multi-cliente); este proyecto vive bajo
  `Flick/`. `flick.pdf` y `ExcelFlick.xlsx` (datos reales con PII) están
  deliberadamente excluidos vía `.gitignore` de la raíz — nunca commitear.
- Todos los tests: `pytest Flick/SegmentacionCampanas/tests/ -v` (63 tests).
- El PDF de documentación funcional (`flick.pdf`) tiene al menos 2 discrepancias
  conocidas con el comportamiento real en producción (ver spec §1) — no confiar
  en él como fuente de verdad sin contrastar contra el `.osts` real cuando exista.
