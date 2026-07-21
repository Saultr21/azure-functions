"""Subida del CSV de campaña a Azure Blob Storage y generación de un enlace
de solo lectura con SAS de expiración corta. El CSV contiene PII (teléfono,
email, dirección), por lo que su contenido nunca se registra en logs."""

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
