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

## Dependencias

Ver `requirements.txt`:

- `azure-functions`
- `openpyxl>=3.1,<4.0`
- `pydantic>=2.6,<3.0`
- `azure-storage-blob>=12.19,<13.0`

Auditadas con `pip-audit` (Gate 4 de ssdlc): sin vulnerabilidades conocidas a
fecha de este commit.

## Desarrollo local

    python -m venv .venv
    .venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    cp local.settings.json.example local.settings.json  # y rellenar los valores
    func start

## Tests

`pytest` es una dependencia de desarrollo (no forma parte del runtime de la
Function ni de `requirements.txt`):

    pip install pytest
    pytest tests/ -v
