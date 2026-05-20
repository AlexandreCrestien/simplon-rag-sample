"""CLI entry point for local PDF ingestion.

Usage:
    uv run python -m rag.cli.ingest
    uv run python -m rag.cli.ingest --docs-dir path/to/docs/

Exit codes:
    0 — always (individual errors are reported and skipped)
"""

from __future__ import annotations

import argparse
import asyncio
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from rag.cli._runner import async_session
from rag.rag.ingestion.pipeline import ingest_pdf
from rag.storage.client import download_file, list_files, ensure_bucket_exists

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_DOCS_DIR = _PROJECT_ROOT / "data" / "docs"

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest PDF files into the vector store")
    parser.add_argument(
        "--docs-dir",
        type=Path,
        required=False,
        default=None,
        help="Directory containing PDF files (local mode). If not set, downloads from GCS/Minio.",
    )
    return parser.parse_args()


@dataclass
class _Summary:
    ingested: int = 0
    skipped: int = 0
    errors: int = 0
    files: list[Path] = field(default_factory=list)


async def _run_from_bucket() -> None:
    """Download PDFs from GCS/Minio and ingest them."""
    ensure_bucket_exists()
    pdf_keys = [k for k in list_files("corpus/") if k.endswith(".pdf")]

    if not pdf_keys:
        print("No PDF files found in bucket under corpus/")
        return

    print(f"Found {len(pdf_keys)} PDF file(s) in bucket")
    summary = _Summary()

    async with async_session() as db:
        for key in pdf_keys:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp_path = Path(tmp.name)
            try:
                download_file(key, tmp_path)
                result = await ingest_pdf(tmp_path, db)
                if result.already_existed:
                    print(f"[SKIP]  {key} — already ingested")
                    summary.skipped += 1
                else:
                    print(f"[OK]    {key} — {result.chunks_created} chunks")
                    summary.ingested += 1
            except Exception as exc:
                print(f"[ERROR] {key} — {exc}")
                summary.errors += 1
            finally:
                tmp_path.unlink(missing_ok=True)

    print(f"\nDone. Ingested: {summary.ingested}, Skipped: {summary.skipped}, Errors: {summary.errors}")


async def _run_from_dir(docs_dir: Path) -> None:
    """Ingest PDFs from a local directory (legacy mode)."""
    if not docs_dir.exists():
        print(f"Docs directory not found: {docs_dir}")
        return

    pdfs = sorted(docs_dir.glob("*.pdf"))
    if not pdfs:
        print(f"No PDF files found in {docs_dir}")
        return

    print(f"Found {len(pdfs)} PDF file(s) in {docs_dir}")
    summary = _Summary(files=pdfs)

    async with async_session() as db:
        for pdf in pdfs:
            try:
                result = await ingest_pdf(pdf, db)
                if result.already_existed:
                    print(f"[SKIP]  {pdf.name} — already ingested")
                    summary.skipped += 1
                else:
                    print(f"[OK]    {pdf.name} — {result.chunks_created} chunks")
                    summary.ingested += 1
            except Exception as exc:
                print(f"[ERROR] {pdf.name} — {exc}")
                summary.errors += 1

    print(f"\nDone. Ingested: {summary.ingested}, Skipped: {summary.skipped}, Errors: {summary.errors}")


def main() -> None:
    args = _parse_args()
    if args.docs_dir:
        asyncio.run(_run_from_dir(args.docs_dir))
    else:
        asyncio.run(_run_from_bucket())


if __name__ == "__main__":
    main()