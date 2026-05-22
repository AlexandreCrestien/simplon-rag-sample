import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag.db.models.document import Document
from rag.db.session import get_db
from rag.rag.ingestion.pipeline import ingest_pdf, ingest_url
from rag.storage.client import ensure_bucket_exists, upload_file

router = APIRouter(prefix="/documents", tags=["ingestion"])


class IngestUrlsRequest(BaseModel):
    urls: list[HttpUrl]
    max_pages: int | None = Field(default=None, gt=0)


@router.post("/ingest-urls")
async def ingest_urls(
    request: IngestUrlsRequest,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    results = []
    for url in request.urls:
        try:
            result = await ingest_url(str(url), db, max_pages=request.max_pages)
            results.append({
                "document_id": str(result.document_id),
                "filename": result.filename,
                "chunks_created": result.chunks_created,
                "already_existed": result.already_existed,
                "error": None,
            })
        except ValueError as e:
            results.append({
                "document_id": None,
                "filename": str(url),
                "chunks_created": 0,
                "already_existed": False,
                "error": str(e),
            })
    return results


@router.post("/ingest")
async def ingest_document(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    try:
        result = await ingest_pdf(tmp_path, db)

        # Upload vers GCS/Minio après ingestion
        ensure_bucket_exists()
        upload_file(tmp_path, f"corpus/{file.filename}")

    finally:
        tmp_path.unlink(missing_ok=True)

    return {
        "document_id": str(result.document_id),
        "filename": result.filename,
        "chunks_created": result.chunks_created,
        "already_existed": result.already_existed,
    }


@router.get("")
async def list_documents(db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(select(Document).order_by(Document.created_at.desc()))
    docs = result.scalars().all()
    return [
        {
            "document_id": str(d.id),
            "filename": d.filename,
            "created_at": d.created_at.isoformat(),
        }
        for d in docs
    ]


@router.delete("/{document_id}")
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(select(Document).where(Document.id == str(document_id)))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.delete(doc)
    await db.commit()
    return {"deleted": str(document_id)}
