# TODO — Flick: Motor de Segmentación con Azure Function

> Last updated: 2026-07-21 (fecha de sesión)
> Current phase: development (implementación completa, pendiente validación manual y despliegue)
> Overall progress: 15/15 tasks del plan completadas

## Completed

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

- [ ] `TASK-016` — Conectar Power Automate → Azure Function
  - Origen: spec §3, plan "fuera de alcance"
  - Prioridad: alta
  - Notas: crear la acción HTTP en el flujo de Power Automate existente,
    apuntando a la URL de la Function desplegada, con el body binario del Excel
    y el `code` (function key) como query param.

- [ ] `TASK-017` — Desplegar infraestructura Azure (Function App, Storage Account, Container)
  - Origen: plan "fuera de alcance"
  - Prioridad: alta
  - Notas: incluir la lifecycle policy de Blob Storage (borrado a 7 días) — ver
    comando de ejemplo en el plan.

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

## Notes

- El repo es `Saultr21/azure-functions` (multi-cliente); este proyecto vive bajo
  `Flick/`. `flick.pdf` y `ExcelFlick.xlsx` (datos reales con PII) están
  deliberadamente excluidos vía `.gitignore` de la raíz — nunca commitear.
- Todos los tests: `pytest Flick/SegmentacionCampanas/tests/ -v` (63 tests).
- El PDF de documentación funcional (`flick.pdf`) tiene al menos 2 discrepancias
  conocidas con el comportamiento real en producción (ver spec §1) — no confiar
  en él como fuente de verdad sin contrastar contra el `.osts` real cuando exista.
