import uvicorn
import uuid
import time
import logging
import sys
from contextvars import ContextVar
from fastapi import Request
from pythonjsonlogger import jsonlogger
from starlette.middleware.base import BaseHTTPMiddleware

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

# --- 2. MIDDLEWARE ---
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = str(uuid.uuid4())
        request_id_var.set(rid)
        start_time = time.time()
        response = await call_next(request)
        duration = round((time.time() - start_time) * 1000, 2)
        logging.info("Fin de requête", extra={"path": request.url.path, "status": response.status_code, "duration_ms": duration})
        return response

# --- 3. INITIALISATION ---
setup_logging()
app = create_app()
app.add_middleware(LoggingMiddleware)

@app.on_event("startup")
async def startup_event():
    setup_logging()
    logging.info("Application démarrée avec logs JSON")

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run("main:app", host="0.0.0.0", port=settings.app_port, reload=True)