"""MinIO (S3-compatible) file service. Creates buckets on startup if missing."""
from __future__ import annotations

import uuid as uuid_module
from typing import BinaryIO

from minio import Minio
from minio.error import S3Error

from app.config import get_settings

_client: Minio | None = None


def get_minio_client() -> Minio:
    global _client
    if _client is None:
        settings = get_settings()
        _client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
    return _client


def ensure_buckets() -> list[str]:
    """Create ulpin-raw-uploads / ulpin-processed if missing (Section 17 pitfall)."""
    settings = get_settings()
    client = get_minio_client()
    created = []
    for bucket in (settings.MINIO_BUCKET_RAW, settings.MINIO_BUCKET_PROCESSED):
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            created.append(bucket)
    return created


def make_object_name(filename: str) -> str:
    safe_name = filename.replace("/", "_").replace("\\", "_")
    return f"{uuid_module.uuid4()}/{safe_name}"


def upload_stream(
    stream: BinaryIO,
    object_name: str,
    length: int,
    content_type: str = "application/octet-stream",
    bucket: str | None = None,
) -> str:
    """Upload a stream to the raw bucket; returns the s3:// URL."""
    settings = get_settings()
    bucket = bucket or settings.MINIO_BUCKET_RAW
    client = get_minio_client()
    client.put_object(bucket, object_name, stream, length, content_type=content_type)
    return f"s3://{bucket}/{object_name}"


def presigned_put_url(
    object_name: str,
    content_type: str = "application/octet-stream",
    expires_seconds: int = 3600,
    bucket: str | None = None,
) -> str:
    settings = get_settings()
    bucket = bucket or settings.MINIO_BUCKET_RAW
    client = get_minio_client()
    return client.presigned_put_object(
        bucket, object_name, expires=expires_seconds
    )


def presigned_get_url(
    object_name: str,
    expires_seconds: int = 3600,
    bucket: str | None = None,
) -> str:
    settings = get_settings()
    bucket = bucket or settings.MINIO_BUCKET_RAW
    client = get_minio_client()
    return client.presigned_get_object(bucket, object_name, expires=expires_seconds)


def object_url(object_name: str, bucket: str | None = None) -> str:
    settings = get_settings()
    bucket = bucket or settings.MINIO_BUCKET_RAW
    return f"s3://{bucket}/{object_name}"


__all__ = [
    "S3Error",
    "ensure_buckets",
    "upload_stream",
    "presigned_put_url",
    "presigned_get_url",
    "object_url",
    "make_object_name",
    "get_minio_client",
]
