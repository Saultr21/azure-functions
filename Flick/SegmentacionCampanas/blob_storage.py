"""Subida del Excel de campaña a Azure Blob Storage y generación de un enlace
de solo lectura con SAS de expiración corta. El Excel contiene PII (teléfono,
email, dirección), por lo que su contenido nunca se registra en logs."""

from datetime import datetime, timedelta, timezone

from azure.storage.blob import BlobServiceClient, BlobSasPermissions, ContentSettings, generate_blob_sas

CONTENT_TYPE_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def subir_excel_y_generar_link(
    *,
    excel_contenido: bytes,
    nombre_archivo: str,
    connection_string: str,
    container: str,
    horas_expiracion: int = 24,
) -> str:
    """Sube el Excel a Blob Storage y devuelve una URL de solo lectura con SAS
    de expiración corta. No se loguea el contenido del Excel (contiene PII)."""
    cliente_servicio = BlobServiceClient.from_connection_string(connection_string)
    cliente_blob = cliente_servicio.get_blob_client(container=container, blob=nombre_archivo)

    cliente_blob.upload_blob(
        excel_contenido,
        overwrite=True,
        content_settings=ContentSettings(
            content_type=CONTENT_TYPE_XLSX,
            content_disposition=f'attachment; filename="{nombre_archivo}"',
        ),
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
