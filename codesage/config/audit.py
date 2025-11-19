from pydantic import BaseModel, Field


class AuditConfig(BaseModel):
    enabled: bool = Field(True, description="Enable or disable audit logging.")
    log_dir: str = Field(".codesage/audit", description="Directory to store audit log files.")
    max_file_size_mb: int = Field(10, description="Maximum size of a single audit log file in MB before rotation.")
