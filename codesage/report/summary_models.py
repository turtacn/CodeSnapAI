from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List


from typing import Dict


class ReportFileSummary(BaseModel):
    path: str = Field(..., description="The relative path to the file.")
    language: str = Field(..., description="The programming language of the file.")
    risk_level: str = Field(..., description="The risk level of the file (e.g., 'low', 'medium', 'high').")
    risk_score: float = Field(..., description="The risk score of the file.")
    loc: int = Field(..., description="The number of lines of code in the file.")
    num_functions: int = Field(..., description="The number of functions in the file.")
    issues_total: int = Field(..., description="The total number of issues in the file.")
    issues_error: int = Field(..., description="The number of error-level issues in the file.")
    issues_warning: int = Field(..., description="The number of warning-level issues in the file.")
    top_issue_rules: List[str] = Field(..., description="A list of the top issue rules found in the file.")


class ReportProjectSummary(BaseModel):
    total_files: int = Field(..., description="The total number of files in the project.")
    high_risk_files: int = Field(..., description="The number of high-risk files in the project.")
    medium_risk_files: int = Field(..., description="The number of medium-risk files in the project.")
    low_risk_files: int = Field(..., description="The number of low-risk files in the project.")
    total_issues: int = Field(..., description="The total number of issues in the project.")
    error_issues: int = Field(..., description="The number of error-level issues in the project.")
    warning_issues: int = Field(..., description="The number of warning-level issues in the project.")
    info_issues: int = Field(..., description="The number of info-level issues in the project.")
    top_rules: List[str] = Field(..., description="A list of the top issue rules found in the project.")
    top_risky_files: List[str] = Field(..., description="A list of the top risky files in the project.")
    languages: List[str] = Field(..., description="A list of the languages found in the project.")
    files_per_language: Dict[str, int] = Field(..., description="A count of files per language.")
