from typing import Any, Dict, List
import yaml
from datetime import datetime

from codesage.snapshot.base_generator import SnapshotGenerator
from codesage.snapshot.models import (
    ProjectSnapshot,
    AnalysisResult,
    FileSnapshot,
    SnapshotMetadata,
    DependencyGraph,
)
from codesage import __version__ as tool_version


class YAMLGenerator(SnapshotGenerator):
    """Generates a YAML snapshot of the project."""

    def generate(
        self, analysis_results: List[AnalysisResult], config: Dict[str, Any]
    ) -> ProjectSnapshot:
        """
        Generates a ProjectSnapshot object from a list of analysis results.
        """
        file_snapshots = [FileSnapshot.model_validate(ar) for ar in analysis_results]
        metadata = SnapshotMetadata(
            version="v1",
            timestamp=datetime.now(),
            tool_version=tool_version,
            config_hash="abc",
        )
        global_metrics = self._aggregate_metrics(analysis_results)
        dependency_graph = DependencyGraph() # Placeholder
        all_patterns = self._collect_all_patterns(analysis_results)
        all_issues = self._collect_all_issues(analysis_results)

        return ProjectSnapshot(
            metadata=metadata,
            files=file_snapshots,
            global_metrics=global_metrics,
            dependency_graph=dependency_graph,
            detected_patterns=all_patterns,
            issues=all_issues,
        )

    def export(self, snapshot: ProjectSnapshot, output_path: str):
        """
        Exports the snapshot to a YAML file.
        """
        snapshot_dict = snapshot.model_dump(mode='json')

        with open(output_path, "w") as f:
            yaml.dump(
                snapshot_dict,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
