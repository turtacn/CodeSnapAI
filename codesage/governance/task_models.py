from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime


class GovernanceTask(BaseModel):
    id: str
    project_name: str
    file_path: str
    language: str
    rule_id: str
    issue_id: Optional[str] = None
    description: str
    priority: int
    risk_level: str
    status: Literal["pending", "in_progress", "done", "skipped"] = "pending"
    llm_hint: Optional[str] = None
    metadata: Dict[str, Any] = {}


class GovernanceTaskGroup(BaseModel):
    id: str
    name: str
    group_by: str
    tasks: List[GovernanceTask]


class GovernancePlan(BaseModel):
    project_name: str
    created_at: datetime
    summary: Dict[str, Any]
    groups: List[GovernanceTaskGroup]
