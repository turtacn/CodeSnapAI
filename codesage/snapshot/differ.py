from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from pydantic import BaseModel

from codesage.snapshot.models import ProjectSnapshot, FileSnapshot, DependencyGraph, ComplexityMetrics


class DependencyDiff(BaseModel):
    """Represents the difference in dependencies between two snapshots."""
    added_edges: List[Tuple[str, str]] = []
    removed_edges: List[Tuple[str, str]] = []

class FileChange(BaseModel):
    """Represents the changes within a single modified file."""
    path: str
    complexity_delta: int = 0

@dataclass
class SnapshotDiff:
    """Represents the difference between two project snapshots."""
    added_files: List[str] = field(default_factory=list)
    removed_files: List[str] = field(default_factory=list)
    modified_files: List[FileChange] = field(default_factory=list)
    dependency_changes: DependencyDiff = field(default_factory=DependencyDiff)


class SnapshotDiffer:
    """Compares two ProjectSnapshot objects and generates a diff."""

    def diff(self, snapshot1: ProjectSnapshot, snapshot2: ProjectSnapshot) -> SnapshotDiff:
        """Calculates the difference between two snapshots."""
        files1 = {f.path: f for f in snapshot1.files}
        files2 = {f.path: f for f in snapshot2.files}

        added_paths, removed_paths, common_paths = self._compare_file_sets(
            set(files1.keys()), set(files2.keys())
        )

        modified_files = self._find_modified_files(files1, files2, common_paths)

        dependency_changes = self._compare_dependencies(
            snapshot1.dependency_graph, snapshot2.dependency_graph
        )

        return SnapshotDiff(
            added_files=list(added_paths),
            removed_files=list(removed_paths),
            modified_files=modified_files,
            dependency_changes=dependency_changes,
        )

    def _compare_file_sets(self, paths1: set, paths2: set) -> Tuple[set, set, set]:
        """Compares two sets of file paths."""
        return paths2 - paths1, paths1 - paths2, paths1 & paths2

    def _find_modified_files(
        self, files1: Dict[str, FileSnapshot], files2: Dict[str, FileSnapshot], common_paths: set
    ) -> List[FileChange]:
        """Identifies modified files by comparing their hashes."""
        modified = []
        for path in common_paths:
            if files1[path].hash != files2[path].hash:
                delta = self._calculate_complexity_delta(files1[path], files2[path])
                modified.append(FileChange(path=path, complexity_delta=delta))
        return modified

    def _calculate_complexity_delta(
        self, file1: FileSnapshot, file2: FileSnapshot
    ) -> int:
        """Calculates the change in cyclomatic complexity."""
        # This assumes ComplexityMetrics has a 'cyclomatic' attribute.
        comp1 = getattr(file1.complexity_metrics, 'cyclomatic', 0)
        comp2 = getattr(file2.complexity_metrics, 'cyclomatic', 0)
        return comp2 - comp1

    def _compare_dependencies(
        self, graph1: DependencyGraph, graph2: DependencyGraph
    ) -> DependencyDiff:
        """Compares two dependency graphs by their edge sets."""
        edges1 = set(tuple(edge) for edge in graph1.edges)
        edges2 = set(tuple(edge) for edge in graph2.edges)

        added = edges2 - edges1
        removed = edges1 - edges2

        return DependencyDiff(
            added_edges=[list(edge) for edge in added],
            removed_edges=[list(edge) for edge in removed],
        )

    def export_diff(self, diff: SnapshotDiff, format: str = "json") -> str:
        """Exports the diff report to a specified format."""
        if format == "json":
            # A more robust implementation would use Pydantic's serialization
            return json.dumps(diff.__dict__, indent=2)
        raise NotImplementedError(f"Format '{format}' is not supported.")

import json
