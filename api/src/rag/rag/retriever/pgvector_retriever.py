
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from rag.config.settings import get_settings
from rag.rag.embeddings import mistral_embeddings


async def similarity_search(
    query: str, db: AsyncSession, k: int | None = None
) -> list[dict]:
    """Find the top-k most relevant document chunks for a query.

    Returns:
        A list of dicts with keys: chunk_id, document_id, content, score, metadata.
        Sorted by cosine similarity descending (score closer to 1 = more similar).
    """
    settings = get_settings()
    top_k = k or settings.retrieval_top_k

    query_embedding = await mistral_embeddings.embed_query(query)

    sql = text("""
        SELECT
            dc.id            AS chunk_id,
            dc.document_id   AS document_id,
            dc.content       AS content,
            dc.chunk_index   AS chunk_index,
            dc.metadata      AS metadata,
            d.filename       AS filename,
            1 - (dc.embedding <=> CAST(:embedding AS vector)) AS score
        FROM document_chunks dc
        JOIN documents d ON d.id = dc.document_id
        WHERE dc.embedding IS NOT NULL
        ORDER BY dc.embedding <=> CAST(:embedding AS vector)
        LIMIT :k
    """)

    result = await db.execute(
        sql,
        {"embedding": str(query_embedding), "k": top_k},
    )
    rows = result.mappings().all()

    return [
        {
            "chunk_id": str(row["chunk_id"]),
            "document_id": str(row["document_id"]),
            "content": row["content"],
            "chunk_index": row["chunk_index"],
            "metadata": dict(row["metadata"]) if row["metadata"] else {},
            "filename": row["filename"],
            "score": float(row["score"]),
        }
        for row in rows
    ]
