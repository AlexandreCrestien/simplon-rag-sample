from functools import lru_cache

from langchain_google_vertexai import VertexAIEmbeddings

from rag.config.settings import get_settings


@lru_cache
def get_embeddings() -> VertexAIEmbeddings:
    settings = get_settings()
    return VertexAIEmbeddings(
        model_name="text-multilingual-embedding-002",
        project=settings.gcp_project,
        location=settings.gcp_location,
    )


async def embed_documents(texts: list[str]) -> list[list[float]]:
    return await get_embeddings().aembed_documents(texts)


async def embed_query(text: str) -> list[float]:
    return await get_embeddings().aembed_query(text)
