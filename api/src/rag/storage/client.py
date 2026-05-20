"""Storage client — Minio (local) or GCS (prod) via boto3 S3-compatible API."""

from __future__ import annotations

import boto3
from botocore.exceptions import ClientError
from pathlib import Path

from rag.config.settings import get_settings


def get_s3_client():
    settings = get_settings()
    if settings.storage_use_gcs:
        return boto3.client(
            "s3",
            endpoint_url="https://storage.googleapis.com",
            aws_access_key_id=settings.storage_access_key,
            aws_secret_access_key=settings.storage_secret_key,
        )
    return boto3.client(
        "s3",
        endpoint_url=settings.storage_endpoint_url,
        aws_access_key_id=settings.storage_access_key,
        aws_secret_access_key=settings.storage_secret_key,
    )


def upload_file(local_path: Path, object_name: str | None = None) -> str:
    """Upload a file to the bucket. Returns the object name."""
    settings = get_settings()
    client = get_s3_client()
    object_name = object_name or local_path.name
    client.upload_file(str(local_path), settings.storage_bucket, object_name)
    return object_name


def download_file(object_name: str, local_path: Path) -> None:
    """Download a file from the bucket to local_path."""
    settings = get_settings()
    client = get_s3_client()
    local_path.parent.mkdir(parents=True, exist_ok=True)
    client.download_file(settings.storage_bucket, object_name, str(local_path))


def list_files(prefix: str = "") -> list[str]:
    """List all files in the bucket with optional prefix."""
    settings = get_settings()
    client = get_s3_client()
    try:
        response = client.list_objects_v2(
            Bucket=settings.storage_bucket,
            Prefix=prefix,
        )
        return [obj["Key"] for obj in response.get("Contents", [])]
    except ClientError:
        return []


def ensure_bucket_exists() -> None:
    """Create the bucket if it doesn't exist (Minio only)."""
    settings = get_settings()
    if settings.storage_use_gcs:
        return
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=settings.storage_bucket)
    except ClientError:
        client.create_bucket(Bucket=settings.storage_bucket)