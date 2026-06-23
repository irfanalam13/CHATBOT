"""S3-compatible object storage (AWS S3 / MinIO) for raw documents."""
from __future__ import annotations

import boto3
from botocore.client import Config

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("services.storage")


class StorageService:
    def __init__(self) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
            config=Config(signature_version="s3v4"),
        )
        self.bucket = settings.S3_BUCKET

    def ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self.bucket)
        except Exception:
            try:
                self._client.create_bucket(Bucket=self.bucket)
            except Exception as e:  # pragma: no cover
                log.warning("bucket_create_failed", error=str(e))

    def put(self, key: str, data: bytes, content_type: str | None = None) -> str:
        self._client.put_object(
            Bucket=self.bucket, Key=key, Body=data,
            ContentType=content_type or "application/octet-stream",
        )
        return key

    def get(self, key: str) -> bytes:
        obj = self._client.get_object(Bucket=self.bucket, Key=key)
        return obj["Body"].read()

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self.bucket, Key=key)

    def presigned_url(self, key: str, expires: int = 3600) -> str:
        return self._client.generate_presigned_url(
            "get_object", Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=expires
        )


_storage: StorageService | None = None


def get_storage() -> StorageService:
    global _storage
    if _storage is None:
        _storage = StorageService()
    return _storage
