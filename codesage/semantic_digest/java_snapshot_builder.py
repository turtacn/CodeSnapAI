from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from codesage.analyzers.java_parser import JavaParser
from codesage.config.risk_baseline import RiskBaselineConfig
from codesage.risk.risk_scorer import score_file_risk, summarize_project_risk
from codesage.snapshot.models import (
    ProjectSnapshot,
    FileSnapshot,
    FileMetrics,
    SnapshotMetadata,
    DependencyGraph,
    ProjectRiskSummary,
)

class SnapshotConfig(dict):
    pass

from codesage.semantic_digest.base_builder import BaseLanguageSnapshotBuilder


class JavaSemanticSnapshotBuilder(BaseLanguageSnapshotBuilder):
    def __init__(self, root_path: Path, config: SnapshotConfig) -> None:
        super().__init__(root_path, config)
        self.parser = JavaParser()
        self.risk_config = RiskBaselineConfig.from_defaults()
        # TODO: Add Java specific rules config if needed

    def build(self) -> ProjectSnapshot:
        files = self._collect_files()

        # In a real scenario, this would be populated by a dependency analyzer
        self.dependency_info = {str(f.relative_to(self.root_path)): [] for f in files}

        file_snapshots = [self._build_file_snapshot(file_path) for file_path in files]
        dep_graph = self._build_dependency_graph(file_snapshots)
        project_risk_summary = self._build_project_risk_summary(file_snapshots)

        metadata = SnapshotMetadata(
            version="1.1",
            timestamp=datetime.now(timezone.utc),
            project_name=self.root_path.name,
            file_count=len(file_snapshots),
            total_size=sum(p.stat().st_size for p in files),
            tool_version="0.2.0",
            config_hash="dummy_hash_v2",
        )

        project = ProjectSnapshot(
            metadata=metadata,
            files=file_snapshots,
            dependencies=dep_graph,
            risk_summary=project_risk_summary,
        )

        # TODO: Run rule engine for Java
        return project

    def _collect_files(self) -> List[Path]:
        files = []
        ignore_paths = self.config.get("ignore_paths", ["target/", "build/", ".gradle/", ".mvn/"])

        for file_path in self.root_path.rglob("*.java"):
            # Normalize path parts for checking
            relative_path = str(file_path.relative_to(self.root_path))

            # Check ignore paths
            ignored = False
            for ignore in ignore_paths:
                if ignore.endswith("/"):
                    # Directory match
                     if ignore.strip("/") in file_path.parts:
                         ignored = True
                         break
                elif ignore in relative_path:
                    ignored = True
                    break

            if not ignored:
                files.append(file_path)
        return files

    def _build_file_snapshot(self, file_path: Path) -> FileSnapshot:
        source_code = file_path.read_text()
        self.parser.parse(source_code)

        functions = self.parser.extract_functions()
        classes = self.parser.extract_classes()
        imports = self.parser.extract_imports()
        package = self.parser.extract_package()

        # Prepend package to class names for Fully Qualified Name
        if package:
            for cls in classes:
                cls.name = f"{package}.{cls.name}"

        complexity_results = self.parser.get_complexity_metrics(source_code)

        # Calculate max complexity from functions
        max_complexity = 0
        high_complexity_functions = 0
        total_complexity = 0

        for func in functions:
            if func.complexity > max_complexity:
                max_complexity = func.complexity
            if func.complexity > self.risk_config.threshold_complexity_high:
                high_complexity_functions += 1
            total_complexity += func.complexity

        avg_complexity = total_complexity / len(functions) if functions else 0.0

        fan_in, fan_out = self._calculate_fan_in_out(str(file_path.relative_to(self.root_path)))

        metrics = FileMetrics(
            lines_of_code=len(source_code.splitlines()),
            num_functions=len(functions),
            num_types=len(classes),
            language_specific={
                "java": {
                    "num_classes": len(classes),
                    "num_methods": len(functions), # functions list includes all methods found in AST
                    "max_cyclomatic_complexity": max_complexity,
                    "avg_cyclomatic_complexity": avg_complexity,
                    "high_complexity_functions": high_complexity_functions,
                    "fan_in": fan_in,
                    "fan_out": fan_out,
                }
            }
        )

        file_risk = score_file_risk(metrics, self.risk_config)

        symbols = {
            "classes": [c.model_dump() for c in classes],
            "functions": [f.model_dump() for f in functions], # Java methods are top-level constructs in our model for now? No, they are inside classes mostly. But extract_functions returns them.
            "imports": [i.model_dump() for i in imports],
        }

        return FileSnapshot(
            path=str(file_path.relative_to(self.root_path)),
            language="java",
            metrics=metrics,
            symbols=symbols,
            risk=file_risk,
        )

    def _build_dependency_graph(self, file_snapshots: List[FileSnapshot]) -> DependencyGraph:
        # Placeholder implementation
        return DependencyGraph(internal=[], external=[])

    def _calculate_fan_in_out(self, file_path: str) -> (int, int):
        fan_out = len(self.dependency_info.get(file_path, []))
        fan_in = 0
        for _, dependencies in self.dependency_info.items():
            if file_path in dependencies:
                fan_in += 1
        return fan_in, fan_out

    def _build_project_risk_summary(self, file_snapshots: List[FileSnapshot]) -> ProjectRiskSummary:
        file_risks = {fs.path: fs.risk for fs in file_snapshots if fs.risk}
        return summarize_project_risk(file_risks)
