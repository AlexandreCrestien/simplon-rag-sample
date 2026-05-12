import httpx
import logging
import time

def create_conversation(base_url: str) -> str:
    """Create a new conversation and return its UUID.

    Raises:
        httpx.HTTPStatusError: if the API returns a non-2xx response.
        httpx.ConnectError: if the API is unreachable.
    """

    logging.info("Frontend: Requesting new conversation")

    with httpx.Client() as client:
        try:
            response = client.post(f"{base_url}/api/v1/conversations")
            # On récupère l'ID de l'API pour lier les logs
            rid = response.headers.get("X-Request-ID", "n/a")
            
            response.raise_for_status()
            conv_id = response.json()["conversation_id"]
            
            logging.info("Frontend: Conversation created", extra={
                "conversation_id": conv_id,
                "request_id": rid
            })
            return conv_id
        except Exception as e:
            logging.error(f"Frontend: Failed to create conversation: {type(e).__name__}", exc_info=True)
            raise


def send_message(base_url: str, conversation_id: str, content: str) -> dict:
    """Send a user message and return the assistant response.

    Returns:
        dict with keys: content (str), sources (list[str]).

    Raises:
        httpx.HTTPStatusError: if the API returns a non-2xx response.
        httpx.ConnectError: if the API is unreachable.
    """

    logging.info("Frontend: Sending message to API", extra={"conversation_id": conversation_id})
    start_time = time.time()

    with httpx.Client() as client:
        try:
            response = client.post(
                f"{base_url}/api/v1/conversations/{conversation_id}/messages",
                json={"content": content},
                timeout=300.0 # L'IA peut être lente
            )
            rid = response.headers.get("X-Request-ID", "n/a")
            duration_ms = round((time.time() - start_time) * 1000, 2)
            
            response.raise_for_status()
            
            logging.info("Frontend: Received API response", extra={
                "conversation_id": conversation_id,
                "request_id": rid,
                "latency_ms": duration_ms,
                "status_code": response.status_code
            })
            
            data = response.json()
            return {
                "content": data.get("content", ""),
                "sources": data.get("sources", []),
            }
        except httpx.HTTPStatusError as e:
            # LOG ERROR pour les exceptions
            logging.error("Frontend: API HTTP Error", extra={
                "conversation_id": conversation_id,
                "status_code": e.response.status_code,
                "request_id": e.response.headers.get("X-Request-ID", "n/a")
            })
            raise
        except Exception as e:
            logging.error(f"Frontend: Unexpected error: {type(e).__name__}", exc_info=True)
            raise
