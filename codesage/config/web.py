from typing import Optional
from pydantic import BaseModel

class WebConsoleConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8080
    snapshot_path: str = ".codesage/snapshot.yaml"
    report_path: Optional[str] = ".codesage/report.json"
    governance_plan_path: Optional[str] = ".codesage/governance_plan.yaml"
    enable_auth: bool = False

    @classmethod
    def default(cls) -> "WebConsoleConfig":
        return cls()
