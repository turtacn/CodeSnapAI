from codesage.history.models import Issue as DB_Issue
from pydantic import BaseModel
from typing import Optional, Dict, List, Any

# Re-export Issue (SQLAlchemy model)
Issue = DB_Issue

class FixSuggestion(BaseModel):
    task_id: str
    new_code: str
    explanation: str
    confidence: float
    patch_context: Dict[str, Any]
    iterations: int = 0
