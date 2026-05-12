import json
import logging
import sys
import uuid

import httpx

# Logger JSON simple pour le frontend
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        return json.dumps(log_data)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logger = logging.getLogger("frontend")
logger.handlers = []
logger.addHandler(handler)
logger.setLevel("INFO")


def create_conversation(base_url: str) -> str:
    """Create a new conversation and return its UUID."""
    request_id = str(uuid.uuid4())
    logger.info("create_conversation", extra={"request_id": request_id})
    with httpx.Client() as client:
        response = client.post(
            f"{base_url}/api/v1/conversations",
            headers={"X-Request-Id": request_id},
        )
        response.raise_for_status()
        return response.json()["conversation_id"]


def send_message(base_url: str, conversation_id: str, content: str) -> dict:
    """Send a user message and return the assistant response."""
    request_id = str(uuid.uuid4())
    logger.info("send_message", extra={
        "request_id": request_id,
        "conversation_id": conversation_id,
    })
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{base_url}/api/v1/conversations/{conversation_id}/messages",
                json={"content": content},
                headers={"X-Request-Id": request_id},
            )
            response.raise_for_status()
            data = response.json()
            logger.info("send_message_success", extra={
                "request_id": request_id,
                "conversation_id": conversation_id,
            })
            return {
                "content": data.get("content", ""),
                "sources": data.get("sources", []),
            }
    except httpx.ConnectError as e:
        logger.error("send_message_network_error", extra={
            "request_id": request_id,
            "error": str(e),
        })
        raise
    except httpx.HTTPStatusError as e:
        logger.error("send_message_http_error", extra={
            "request_id": request_id,
            "status_code": e.response.status_code,
        })
        raise