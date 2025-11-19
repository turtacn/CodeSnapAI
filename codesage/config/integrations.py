from typing import Optional

from pydantic import BaseModel, Field

from codesage.integrations.webhook import WebhookConfig


class IntegrationsConfig(BaseModel):
    webhook: Optional[WebhookConfig] = Field(None, description="Webhook integration configuration.")
    file_export_dir: Optional[str] = Field(None, description="Directory for exporting integration files.")
