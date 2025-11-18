from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class AnalysisResult(BaseModel):
    pass


class DependencyGraph(BaseModel):
    internal: List[Dict[str, str]] = Field(default_factory=list, description="List of internal dependencies.")
    external: List[str] = Field(default_factory=list, description="List of external dependencies.")
    edges: List[Tuple[str, str]] = Field(default_factory=list, description="A list of tuples representing directed edges for backward compatibility.")

# --- Models for Backward Compatibility ---

class DetectedPattern(BaseModel):
    pass

class AnalysisIssue(BaseModel):
    # This is a legacy model, prefer the new `Issue` model.
    pass

class ComplexityMetrics(BaseModel):
    cyclomatic: int = 0

class ASTSummary(BaseModel):
    function_count: int = Field(..., description="Number of functions in the file.")
    class_count: int = Field(..., description="Number of classes in the file.")
    import_count: int = Field(..., description="Number of imports in the file.")
    comment_lines: int = Field(..., description="Number of comment lines in the file.")

# --- Current Models ---

class FileMetrics(BaseModel):
    num_classes: int = Field(0, description="Number of classes in the file.")
    num_functions: int = Field(0, description="Number of functions in the file.")
    num_methods: int = Field(0, description="Number of methods in the file.")
    has_async: bool = Field(False, description="Whether the file contains async code.")
    uses_type_hints: bool = Field(False, description="Whether the file uses type hints.")
    lines_of_code: int = Field(0, description="Number of lines of code.")
    max_cyclomatic_complexity: int = Field(0, description="Maximum cyclomatic complexity of any function.")
    avg_cyclomatic_complexity: float = Field(0.0, description="Average cyclomatic complexity of functions.")
    high_complexity_functions: int = Field(0, description="Number of functions with high cyclomatic complexity.")
    fan_in: int = Field(0, description="Number of files that depend on this file.")
    fan_out: int = Field(0, description="Number of files this file depends on.")


class FileRisk(BaseModel):
    risk_score: float = Field(..., description="The calculated risk score (0-1).")
    level: Literal["low", "medium", "high"] = Field(..., description="The risk level.")
    factors: List[str] = Field(default_factory=list, description="Factors contributing to the risk score.")

class IssueLocation(BaseModel):
    file_path: str = Field(..., description="The path to the file where the issue was found.")
    line: int = Field(..., description="The line number of the issue.")
    column: Optional[int] = Field(None, description="The column number of the issue.")

class Issue(BaseModel):
    id: str = ""
    rule_id: str = Field(..., description="The identifier of the rule that was triggered.")
    severity: Literal["info", "warning", "error"] = Field(..., description="The severity of the issue.")
    message: str = Field(..., description="A human-readable description of the issue.")
    location: IssueLocation = Field(..., description="The location of the issue in the codebase.")
    symbol: Optional[str] = Field(None, description="The symbol (e.g., function, class) associated with the issue.")
    tags: List[str] = Field(default_factory=list, description="Tags for categorizing the issue.")
    suggested_fix_summary: Optional[str] = Field(None, description="A brief summary of a suggested fix.")
    llm_fix_hint: Optional[str] = Field(None, description="LLM generated fix hint.")
    llm_rationale: Optional[str] = Field(None, description="LLM generated rationale for the fix.")
    llm_status: Literal["not_requested", "requested", "succeeded", "failed"] = Field("not_requested", description="The status of the LLM suggestion.")
    llm_model: Optional[str] = Field(None, description="The LLM model used to generate the suggestion.")
    llm_last_updated_at: Optional[datetime] = Field(None, description="The timestamp when the LLM suggestion was last updated.")

    @model_validator(mode="before")
    def generate_id(cls, data):
        if isinstance(data, dict) and "id" not in data:
            rule_id = data.get("rule_id")
            location = data.get("location")
            if rule_id and location:
                if isinstance(location, dict):
                    file_path = location.get("file_path", "unknown-file")
                    line = location.get("line", 0)
                    data["id"] = f"{rule_id}:{file_path}:{line}"
                elif isinstance(location, IssueLocation):
                    data["id"] = f"{rule_id}:{location.file_path}:{location.line}"
        return data

class ProjectIssuesSummary(BaseModel):
    total_issues: int = Field(..., description="The total number of issues found.")
    by_severity: Dict[str, int] = Field(default_factory=dict, description="A count of issues grouped by severity.")
    by_rule: Dict[str, int] = Field(default_factory=dict, description="A count of issues grouped by rule ID.")


class LLMCallStats(BaseModel):
    total_requests: int = Field(0, description="Total number of LLM requests made.")
    succeeded: int = Field(0, description="Number of successful LLM requests.")
    failed: int = Field(0, description="Number of failed LLM requests.")


class FileSnapshot(BaseModel):
    path: str = Field(..., description="The relative path to the file.")
    language: str = Field(..., description="The programming language of the file.")
    metrics: Optional[FileMetrics] = Field(None, description="A summary of the file's metrics.")
    symbols: Optional[Dict[str, Any]] = Field(default_factory=dict, description="A dictionary of symbols defined in the file.")
    risk: Optional[FileRisk] = Field(None, description="Risk assessment for the file.")
    issues: List[Issue] = Field(default_factory=list, description="A list of issues identified in the file.")

    # Old fields for compatibility
    hash: Optional[str] = Field(None, description="The SHA256 hash of the file content.")
    lines: Optional[int] = Field(None, description="The total number of lines in the file.")
    ast_summary: Optional[ASTSummary] = Field(None, description="A summary of the file's AST.")
    complexity_metrics: Optional[ComplexityMetrics] = Field(None, description="Complexity metrics for the file.")
    detected_patterns: List[DetectedPattern] = Field(default_factory=list, description="Patterns detected in the file.")
    analysis_issues: List[AnalysisIssue] = Field(default_factory=list, description="Legacy issues field.")

class ProjectRiskSummary(BaseModel):
    avg_risk: float = Field(..., description="Average risk score across all files.")
    high_risk_files: int = Field(..., description="Number of high-risk files.")
    medium_risk_files: int = Field(..., description="Number of medium-risk files.")
    low_risk_files: int = Field(..., description="Number of low-risk files.")

class SnapshotMetadata(BaseModel):
    version: str = Field(..., description="The version of the snapshot (e.g., 'v1', 'v2').")
    timestamp: datetime = Field(..., description="The timestamp when the snapshot was created.")
    project_name: str = Field(..., description="The name of the project.")
    file_count: int = Field(..., description="The number of files in the snapshot.")
    total_size: int = Field(..., description="The total size of the files in the snapshot.")
    git_commit: Optional[str] = Field(None, description="The git commit hash when the snapshot was taken.")
    tool_version: str = Field(..., description="The version of the codesage tool.")
    config_hash: str = Field(..., description="The MD5 hash of the configuration file used for this snapshot.")


class ProjectSnapshot(BaseModel):
    metadata: SnapshotMetadata = Field(..., description="Metadata for the snapshot.")
    files: List[FileSnapshot] = Field(..., description="A list of snapshots for each file in the project.")
    dependencies: Optional[DependencyGraph] = Field(None, description="The project's dependency graph.")
    risk_summary: Optional[ProjectRiskSummary] = Field(None, description="Summary of project risk.")
    issues_summary: Optional[ProjectIssuesSummary] = Field(None, description="Summary of project issues.")
    llm_stats: Optional[LLMCallStats] = Field(None, description="Statistics about LLM calls.")

    # Old fields for compatibility
    global_metrics: Optional[Dict[str, Any]] = Field(None, description="Project-wide metrics.")
    dependency_graph: Optional[DependencyGraph] = Field(None, description="The project's dependency graph for backward compatibility.")
    detected_patterns: List[DetectedPattern] = Field(default_factory=list, description="A list of all patterns detected across the project.")
    issues: List[AnalysisIssue] = Field(default_factory=list, description="A list of all issues identified across the project.")
