from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# Placeholder for models from other modules, assuming they are Pydantic models
class AnalysisResult(BaseModel):
    pass

from typing import Tuple


class DependencyGraph(BaseModel):
    edges: List[Tuple[str, str]] = Field(default_factory=list, description="A list of tuples representing directed edges.")


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

class FileSnapshot(BaseModel):
    """Represents a snapshot of a single file."""
    path: str = Field(..., description="The relative path to the file.")
    language: str = Field(..., description="The programming language of the file.")
    hash: str = Field(..., description="The SHA256 hash of the file content.")
    lines: int = Field(..., description="The total number of lines in the file.")
    ast_summary: ASTSummary = Field(..., description="A summary of the file's AST.")
    complexity_metrics: ComplexityMetrics = Field(..., description="Complexity metrics for the file.")
    detected_patterns: List[DetectedPattern] = Field(default_factory=list, description="Patterns detected in the file.")
    issues: List[AnalysisIssue] = Field(default_factory=list, description="Issues identified in the file.")

class SnapshotMetadata(BaseModel):
    """Metadata associated with a project snapshot."""
    version: str = Field(..., description="The version of the snapshot (e.g., 'v1', 'v2').")
    timestamp: datetime = Field(..., description="The timestamp when the snapshot was created.")
    git_commit: Optional[str] = Field(None, description="The git commit hash when the snapshot was taken.")
    tool_version: str = Field(..., description="The version of the codesage tool.")
    config_hash: str = Field(..., description="The MD5 hash of the configuration file used for this snapshot.")

class ProjectSnapshot(BaseModel):
    """Represents a snapshot of the entire project."""
    metadata: SnapshotMetadata = Field(..., description="Metadata for the snapshot.")
    files: List[FileSnapshot] = Field(..., description="A list of snapshots for each file in the project.")
    global_metrics: Dict[str, Any] = Field(..., description="Project-wide metrics (e.g., total lines, language distribution).")
    dependency_graph: DependencyGraph = Field(..., description="The project's dependency graph.")
    detected_patterns: List[DetectedPattern] = Field(..., description="A list of all patterns detected across the project.")
    issues: List[AnalysisIssue] = Field(..., description="A list of all issues identified across the project.")
