from app.services.storage.base import BaseFileUploader


def get_file_uploader() -> BaseFileUploader:
    """Return the active storage backend based on STORAGE_BACKEND env var."""
    from app.core.config import settings

    if getattr(settings, "STORAGE_BACKEND", "local").lower() == "s3":
        import aioboto3
        from app.services.storage.s3 import S3FileUploader

        session = aioboto3.Session(
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION,
        )
        return S3FileUploader(
            session=session,
            bucket=settings.S3_BUCKET,
            base_url=settings.OSS_URL,
            endpoint_url=settings.S3_ENDPOINT_URL or None,
        )

    from app.services.storage.local import LocalFileUploader

    return LocalFileUploader(
        upload_dir=settings.UPLOAD_DIR,
        base_url=settings.OSS_URL,
    )
