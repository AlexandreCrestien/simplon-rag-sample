from functools import lru_cache
from langchain_ollama import OllamaEmbeddings

@lru_cache
def get_embeddings() -> OllamaEmbeddings:
    return OllamaEmbeddings(
        model="mxbai-embed-large",
        base_url="http://host.docker.internal:11434",
    )

async def embed_documents(texts: list[str]) -> list[list[float]]:
    return await get_embeddings().aembed_documents(texts)

async def embed_query(text: str) -> list[float]:
    return await get_embeddings().aembed_query(text)
