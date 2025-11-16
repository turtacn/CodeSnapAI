import json
import hashlib
import subprocess
from datetime import datetime
from typing import Any, Dict, List

import jsonschema

from codesage.snapshot.base_generator import SnapshotGenerator
from codesage.snapshot.models import (
    ProjectSnapshot,
    AnalysisResult,
    FileSnapshot,
    SnapshotMetadata,
    DependencyGraph,
)
from codesage import __version__ as tool_version


class JSONGenerator(SnapshotGenerator):
    """Generates a JSON snapshot of the project."""

    def generate(
        self, analysis_results: List[AnalysisResult], config: Dict[str, Any]
    ) -> ProjectSnapshot:
        """
        Generates a ProjectSnapshot object from a list of analysis results.
        """
        # 1. Create FileSnapshot objects from analysis results
        # We assume analysis_results is a list of dicts that can initialize FileSnapshot
        file_snapshots = [FileSnapshot.model_validate(ar) for ar in analysis_results]

        # 2. Generate metadata
        metadata = self._create_metadata(config)

        # 3. Aggregate project-level data
        global_metrics = self._aggregate_metrics(analysis_results)
        all_patterns = self._collect_all_patterns(analysis_results)
        all_issues = self._collect_all_issues(analysis_results)

        # For now, we assume dependency graph is not part of the file-level results
        # and create an empty one. A real implementation might merge graphs.
        dependency_graph = DependencyGraph()

        # 4. Assemble the ProjectSnapshot
        return ProjectSnapshot(
            metadata=metadata,
            files=file_snapshots,
            global_metrics=global_metrics,
            dependency_graph=dependency_graph,
            detected_patterns=all_patterns,
            issues=all_issues,
        )

    def _create_metadata(self, config: Dict[str, Any]) -> SnapshotMetadata:
        """Creates the metadata for the snapshot."""
        git_commit = self._get_git_commit()
        config_hash = hashlib.md5(
            json.dumps(config, sort_keys=True).encode("utf-8")
        ).hexdigest()

        return SnapshotMetadata(
            version="v1",  # Versioning will be handled by SnapshotVersionManager
            timestamp=datetime.now(),
            git_commit=git_commit,
            tool_version=tool_version,
            config_hash=config_hash,
        )

    def _get_git_commit(self) -> str | None:
        """Retrieves the current git commit hash."""
        try:
            commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
            ).strip().decode("utf-8")
            return commit
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def export(
        self,
        snapshot: ProjectSnapshot,
        output_path: str,
        pretty: bool = True,
        validate: bool = True,
    ):
        """Exports the snapshot to a JSON file."""
        snapshot_dict = snapshot.model_dump(mode='json')

        if validate:
            self._validate_schema(snapshot_dict)

        with open(output_path, "w") as f:
            if pretty:
                json.dump(snapshot_dict, f, indent=2)
            else:
                json.dump(snapshot_dict, f, separators=(",", ":"))

    def _validate_schema(self, snapshot_dict: Dict[str, Any]):
        """Validates the snapshot against the JSON schema."""
        schema = self._get_schema()
        jsonschema.validate(instance=snapshot_dict, schema=schema)

    def _get_schema(self) -> Dict[str, Any]:
        """Retrieves the JSON schema for ProjectSnapshot."""
        return ProjectSnapshot.model_json_schema()

    def generate_schema(self, output_path: str):
        """Generates and saves the JSON schema for the ProjectSnapshot model."""
        schema = self._get_schema()
        with open(output_path, "w") as f:
            json.dump(schema, f, indent=2)
