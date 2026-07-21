# Flick — Chatbot de campañas de marketing posventa

Proyecto: sustituir Power Automate + Office Scripts por una Azure Function en
Python como motor de segmentación de clientes para las 5 campañas del chatbot
de Flick en Microsoft Copilot Studio.

## Estructura

```
Flick/
  docs/superpowers/specs/   # Specs de diseño (formato superpowers:brainstorming)
  office-scripts-actuales/  # Office Scripts (.osts) en producción hoy — referencia
                             # de comportamiento real para la migración
  SegmentacionCampanas/     # (próximamente) Azure Function que sustituye a los
                             # Office Scripts
```

## Documentos clave

- [`docs/superpowers/specs/2026-07-21-motor-segmentacion-azure-function-design.md`](docs/superpowers/specs/2026-07-21-motor-segmentacion-azure-function-design.md) —
  diseño completo: arquitectura, restricciones de acceso, seguridad, discrepancias
  encontradas entre la documentación funcional y el código real.

## Nota de confidencialidad

El PDF de documentación funcional (`flick.pdf`) y el Excel maestro con datos reales
de clientes (`ExcelFlick.xlsx`) contienen información confidencial e PII, y están
deliberadamente excluidos de este repositorio (ver `.gitignore` en la raíz).
