import uvicorn
import uuid
import time
import logging
import sys
from contextvars import ContextVar
from fastapi import Request
from pythonjsonlogger import jsonlogger
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, make_asgi_app

from rag.api.app import create_app
from rag.config.settings import get_settings

# --- 1. CONFIG LOGGING ---
request_id_var: ContextVar[str] = ContextVar("request_id", default="n/a")

class StructuredJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(StructuredJsonFormatter, self).add_fields(log_record, record, message_dict)
        log_record['request_id'] = request_id_var.get()
        log_record['level'] = record.levelname

def setup_logging():
    formatter = StructuredJsonFormatter('%(asctime)s %(levelname)s %(message)s')
    loggers = [logging.getLogger(), logging.getLogger("uvicorn"), logging.getLogger("uvicorn.access"), logging.getLogger("sqlalchemy.engine")]
    for logger_name in loggers:
        target_logger = logging.getLogger(logger_name) if isinstance(logger_name, str) else logger_name
        for handler in target_logger.handlers[:]:
            target_logger.removeHandler(handler)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        target_logger.addHandler(handler)
        target_logger.propagate = False
    logging.getLogger().setLevel(logging.INFO)

# --- 2. DEFINITION DES METRIQUES (Toujours avant le Middleware) ---
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total", 
    "Total des requêtes HTTP", 
    ["method", "endpoint", "status"]
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "Latence des requêtes en secondes",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

# --- 3. MIDDLEWARE (Défini avant l'utilisation dans app) ---
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = str(uuid.uuid4())
        request_id_var.set(rid)
        
        if request.url.path == "/metrics":
            return await call_next(request)
            
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time
        
        endpoint = request.url.path
        HTTP_REQUESTS_TOTAL.labels(
            method=request.method, 
            endpoint=endpoint, 
            status=response.status_code
        ).inc()
        
        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=request.method, 
            endpoint=endpoint
        ).observe(duration)

        logging.info("Fin de requête", extra={
            "path": endpoint, 
            "status": response.status_code, 
            "duration_ms": round(duration * 1000, 2)
        })
        return response

# --- 4. INITIALISATION DE L'APPLICATION ---
setup_logging()
app = create_app()

# On ajoute le middleware une fois qu'il est défini
app.add_middleware(LoggingMiddleware)

# Exposition de /metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

@app.on_event("startup")
async def startup_event():
    logging.info("Application démarrée avec logs JSON et métriques Prometheus")

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run("main:app", host="0.0.0.0", port=settings.app_port, reload=True)