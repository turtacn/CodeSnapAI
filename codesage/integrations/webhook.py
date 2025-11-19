from typing import Dict, Any
import httpx
from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger(__name__)

class WebhookConfig(BaseModel):
    url: str = Field(..., description="The URL of the webhook.")
    timeout_seconds: int = Field(10, description="The timeout in seconds for the webhook request.")
    headers: Dict[str, str] = Field(default_factory=dict, description="The headers to send with the webhook request.")
    enabled: bool = Field(False, description="Whether the webhook is enabled.")

class WebhookClient:
    def __init__(self, config: WebhookConfig) -> None:
        self._config = config

    def send(self, event_type: str, payload: Dict[str, Any]) -> None:
        if not self._config.enabled:
            return

        try:
            with httpx.Client() as client:
                response = client.post(
                    self._config.url,
                    json={"event_type": event_type, "payload": payload},
                    headers=self._config.headers,
                    timeout=self._config.timeout_seconds,
                )
                response.raise_for_status()
                logger.info("webhook_sent_successfully", url=self._config.url, event_type=event_type)
        except httpx.RequestError as e:
            logger.error("webhook_request_failed", url=self._config.url, error=str(e))
