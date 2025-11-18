from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Literal

from pydantic import BaseModel, Field


class AnalysisResult(BaseModel):
    pass


class DependencyGraph(BaseModel):
    internal: List[Dict[str, str]] = Field(default_factory=list, description="List of internal dependencies.")
    external: List[str] = Field(default_factory=list, description="List of external dependencies.")
    edges: List[Tuple[str, str]] = Field(default_factory=list, description="A list of tuples representing directed edges for backward compatibility.")


class DetectedPattern(BaseModel):
    pass


class AnalysisIssue(BaseModel):
    pass


class ComplexityMetrics(BaseModel):
    cyclomatic: int = 0


class ASTSummary(BaseModel):
    """Summary of the Abstract Syntax Tree for a file."""
    function_count: int = Field(..., description="Number of functions in the file.")
    class_count: int = Field(..., description="Number of classes in the file.")
    import_count: int = Field(..., description="Number of imports in the file.")
    comment_lines: int = Field(..., description="Number of comment lines in the file.")


class FileMetrics(BaseModel):
    num_classes: int = Field(0, description="Number of classes in the file.")
    num_functions: int = Field(0, description="Number of functions in the file.")
    num_methods: int = Field(0, description="Number of methods in the file.")
    has_async: bool = Field(False, description="Whether the file contains async code.")
    uses_type_hints: bool = Field(False, description="Whether the file uses type hints.")

    # New complexity and coupling metrics
    lines_of_code: int = Field(0, description="Number of lines of code.")
    max_cyclomatic_complexity: int = Field(0, description="Maximum cyclomatic complexity of any function.")
    avg_cyclomatic_complexity: float = Field(0.0, description="Average cyclomatic complexity of functions.")
    high_complexity_functions: int = Field(0, description="Number of functions with high cyclomatic complexity.")
    fan_in: int = Field(0, description="Number of files that depend on this file.")
    fan_out: int = Field(0, description="Number of files this file depends on.")


class FileRisk(BaseModel):
    """Risk assessment for a single file."""
    risk_score: float = Field(..., description="The calculated risk score (0-1).")
    level: Literal["low", "medium", "high"] = Field(..., description="The risk level.")
    factors: List[str] = Field(default_factory=list, description="Factors contributing to the risk score.")


class ProjectRiskSummary(BaseModel):
    """Summary of risk across the project."""
    avg_risk: float = Field(..., description="Average risk score across all files.")
    high_risk_files: int = Field(..., description="Number of high-risk files.")
    medium_risk_files: int = Field(..., description="Number of medium-risk files.")
    low_risk_files: int = Field(..., description="Number of low-risk files.")


class FileSnapshot(BaseModel):
    """Represents a snapshot of a single file."""
    path: str = Field(..., description="The relative path to the file.")
    language: str = Field(..., description="The programming language of the file.")

    metrics: Optional[FileMetrics] = Field(None, description="A summary of the file's metrics.")
    symbols: Optional[Dict[str, Any]] = Field(default_factory=dict, description="A dictionary of symbols defined in the file.")
    risk: Optional[FileRisk] = Field(None, description="Risk assessment for the file.")

    hash: Optional[str] = Field(None, description="The SHA256 hash of the file content.")
    lines: Optional[int] = Field(None, description="The total number of lines in the file.")
    ast_summary: Optional[ASTSummary] = Field(None, description="A summary of the file's AST.")
    complexity_metrics: Optional[ComplexityMetrics] = Field(None, description="Complexity metrics for the file.")

    detected_patterns: List[DetectedPattern] = Field(default_factory=list, description="Patterns detected in the file.")
    issues: List[AnalysisIssue] = Field(default_factory=list, description="Issues identified in the file.")


class SnapshotMetadata(BaseModel):
    """Metadata associated with a project snapshot."""
    version: str = Field(..., description="The version of the snapshot (e.g., 'v1', 'v2').")
    timestamp: datetime = Field(..., description="The timestamp when the snapshot was created.")
    project_name: str = Field(..., description="The name of the project.")
    file_count: int = Field(..., description="The number of files in the snapshot.")
    total_size: int = Field(..., description="The total size of the files in the snapshot.")
    git_commit: Optional[str] = Field(None, description="The git commit hash when the snapshot was taken.")
    tool_version: str = Field(..., description="The version of the codesage tool.")
    config_hash: str = Field(..., description="The MD5 hash of the configuration file used for this snapshot.")


class ProjectSnapshot(BaseModel):
    """Represents a snapshot of the entire project."""
    metadata: SnapshotMetadata = Field(..., description="Metadata for the snapshot.")
    files: List[FileSnapshot] = Field(..., description="A list of snapshots for each file in the project.")
    dependencies: Optional[DependencyGraph] = Field(None, description="The project's dependency graph.")
    risk_summary: Optional[ProjectRiskSummary] = Field(None, description="Summary of project risk.")

    global_metrics: Optional[Dict[str, Any]] = Field(None, description="Project-wide metrics (e.g., total lines, language distribution).")
    dependency_graph: Optional[DependencyGraph] = Field(None, description="The project's dependency graph for backward compatibility.")

    detected_patterns: List[DetectedPattern] = Field(default_factory=list, description="A list of all patterns detected across the project.")
    issues: List[AnalysisIssue] = Field(default_factory=list, description="A list of all issues identified across the project.")
