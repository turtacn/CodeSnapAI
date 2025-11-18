from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from codesage.analyzers.python_parser import PythonParser
from codesage.config.risk_baseline import RiskBaselineConfig
from codesage.config.rules_python_baseline import RulesPythonBaselineConfig
from codesage.risk.python_complexity import analyze_file_complexity
from codesage.risk.risk_scorer import score_file_risk, summarize_project_risk
from codesage.rules.engine import RuleEngine
from codesage.rules.python_ruleset_baseline import get_python_baseline_rules
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

class PythonSemanticSnapshotBuilder:
    def __init__(self, root_path: Path, config: SnapshotConfig) -> None:
        self.root_path = root_path
        self.config = config
        self.parser = PythonParser()
        self.risk_config = RiskBaselineConfig.from_defaults()
        self.rules_config = RulesPythonBaselineConfig.default() # This would be loaded from main config in a real app

    def build(self) -> ProjectSnapshot:
        files = self._collect_python_files()

        # In a real scenario, this would be populated by a dependency analyzer
        self.dependency_info = {str(f.relative_to(self.root_path)): [] for f in files}

        file_snapshots = [self._build_file_snapshot(file_path) for file_path in files]
        dep_graph = self._build_dependency_graph(file_snapshots)
        project_risk_summary = self._build_project_risk_summary(file_snapshots)

        metadata = SnapshotMetadata(
            version="1.1", # Version bump for new features
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

        # Run the rule engine as the final step
        if self.rules_config.enabled:
            rules = get_python_baseline_rules(self.rules_config)
            engine = RuleEngine(rules=rules)
            project_with_issues = engine.run(project, self.rules_config)
            return project_with_issues

        return project

    def _collect_python_files(self) -> List[Path]:
        return list(self.root_path.rglob("*.py"))

    def _build_file_snapshot(self, file_path: Path) -> FileSnapshot:
        source_code = file_path.read_text()
        self.parser.parse(source_code)

        functions = self.parser.extract_functions()
        classes = self.parser.extract_classes()

        complexity_results = analyze_file_complexity(source_code, self.risk_config.threshold_complexity_high)
        fan_in, fan_out = self._calculate_fan_in_out(str(file_path.relative_to(self.root_path)))

        metrics = FileMetrics(
            num_classes=len(classes),
            num_functions=len(functions),
            num_methods=sum(len(c.methods) for c in classes),
            has_async=any(f.is_async for f in functions) or any(m.is_async for c in classes for m in c.methods),
            uses_type_hints=False, # Placeholder
            lines_of_code=complexity_results.loc if complexity_results else 0,
            max_cyclomatic_complexity=complexity_results.max_cyclomatic_complexity if complexity_results else 0,
            avg_cyclomatic_complexity=complexity_results.avg_cyclomatic_complexity if complexity_results else 0.0,
            high_complexity_functions=complexity_results.high_complexity_functions if complexity_results else 0,
            fan_in=fan_in,
            fan_out=fan_out,
        )

        file_risk = score_file_risk(metrics, self.risk_config)

        symbols = {
            "classes": [c.name for c in classes],
            "functions": [f.name for f in functions],
        }

        return FileSnapshot(
            path=str(file_path.relative_to(self.root_path)),
            language="python",
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
