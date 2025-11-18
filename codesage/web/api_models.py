from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class ApiProjectSummary(BaseModel):
    project_name: str
    total_files: int
    languages: List[str]
    files_per_language: Dict[str, int]
    high_risk_files: int
    total_issues: int

class ApiFileListItem(BaseModel):
    path: str
    language: str
    risk_level: str
    risk_score: float
    issues_total: int

class ApiFileDetail(BaseModel):
    path: str
    language: Optional[str]
    metrics: Dict[str, Any]
    risk: Dict[str, Any]
    issues: List[Dict[str, Any]]

class ApiGovernanceTask(BaseModel):
    task_id: str
    rule_id: str
    file_path: str
    status: str
    metadata: Dict[str, Any]
