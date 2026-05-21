"""Storage client — fake-gcs-server (local) ou GCS (prod) via google-cloud-storage."""

from __future__ import annotations

from pathlib import Path

from google.api_core.client_options import ClientOptions
from google.cloud import storage

from rag.config.settings import get_settings


def get_gcs_client() -> storage.Client:
    settings = get_settings()
    if settings.storage_endpoint_url:
        # Local : pointe vers fake-gcs-server
        return storage.Client(
            project="local",
            client_options=ClientOptions(api_endpoint=settings.storage_endpoint_url),
        )
    # Prod GCP : utilise les credentials automatiques (ADC)
    return storage.Client()


def upload_file(local_path: Path, object_name: str | None = None) -> str:
    settings = get_settings()
    client = get_gcs_client()
    bucket = client.bucket(settings.storage_bucket)
    object_name = object_name or local_path.name
    bucket.blob(object_name).upload_from_filename(str(local_path))
    return object_name


def download_file(object_name: str, local_path: Path) -> None:
    settings = get_settings()
    client = get_gcs_client()
    local_path.parent.mkdir(parents=True, exist_ok=True)
    bucket = client.bucket(settings.storage_bucket)
    bucket.blob(object_name).download_to_filename(str(local_path))


def list_files(prefix: str = "") -> list[str]:
    settings = get_settings()
    client = get_gcs_client()
    try:
        blobs = client.list_blobs(settings.storage_bucket, prefix=prefix)
        return [blob.name for blob in blobs]
    except Exception:
        return []


def ensure_bucket_exists() -> None:
    settings = get_settings()
    client = get_gcs_client()
    try:
        client.get_bucket(settings.storage_bucket)
    except Exception:
        client.create_bucket(settings.storage_bucket)