from typing import List, Tuple, Any, Dict, Set
from pydantic import BaseModel

class CodeLocation(BaseModel):
    file: str
    start_line: int
    end_line: int

class ComplexityMetrics(BaseModel):
    cyclomatic_complexity: int
    cognitive_complexity: int
    halstead_volume: float
    max_function_complexity: int
    avg_function_complexity: float

class DependencyGraph(BaseModel):
    nodes: List[str]
    edges: List[Tuple[str, str]]
    cycles: List[List[str]]
    max_depth: int

class DetectedPattern(BaseModel):
    pattern_type: str
    confidence: float
    location: CodeLocation
    description: str

class AnalysisIssue(BaseModel):
    severity: str
    category: str
    message: str
    location: CodeLocation

class AnalysisResult(BaseModel):
    file_path: str
    complexity_metrics: ComplexityMetrics
    dependencies: DependencyGraph
    detected_patterns: List[DetectedPattern]
    issues: List[AnalysisIssue]
