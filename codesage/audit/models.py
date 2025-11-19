from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class AuditEvent(BaseModel):
    timestamp: datetime = Field(..., description="The timestamp of the audit event.")
    event_type: str = Field(..., description="The type of event, e.g., 'cli.snapshot'.")
    project_name: Optional[str] = Field(None, description="The name of the project, if applicable.")
    command: str = Field(..., description="The command that was executed.")
    args: Dict[str, Any] = Field(..., description="The arguments passed to the command.")
    extra: Dict[str, Any] = Field(default_factory=dict, description="Additional context for the event.")
