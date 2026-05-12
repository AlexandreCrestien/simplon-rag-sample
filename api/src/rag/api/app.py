import uuid
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from rag.api.routers import chat, eval, health, ingestion
from rag.db.session import engine
from rag.observability.logging_config import setup_logging, request_id_var

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("API démarrée")
    yield
    await engine.dispose()
    logger.info("API arrêtée")

def create_app() -> FastAPI:
    app = FastAPI(
        title="Simplon RAG Sample API",
        description="Sample RAG support chatbot API",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        # Lit le header X-Request-Id ou en génère un nouveau
        request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
        # Stocke l'ID dans le contexte de la requête
        token = request_id_var.set(request_id)
        logger.info("requête reçue", extra={"method": request.method, "path": request.url.path})
        response = await call_next(request)
        # Remet l'ID dans la réponse pour que le client puisse le voir
        response.headers["X-Request-Id"] = request_id
        request_id_var.reset(token)
        return response

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(ingestion.router, prefix="/api/v1")
    app.include_router(chat.router, prefix="/api/v1")
    app.include_router(eval.router, prefix="/api/v1")

    return app