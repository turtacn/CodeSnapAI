from pathlib import Path
from typing import Any, Dict, List
import yaml

from codesage.snapshot.base_generator import SnapshotGenerator
from codesage.snapshot.models import ProjectSnapshot


class YAMLGenerator(SnapshotGenerator):
    def generate(self, analysis_results: List[Dict[str, Any]]) -> ProjectSnapshot:
        # This generator is now primarily for serialization.
        if len(analysis_results) == 1 and isinstance(analysis_results[0], ProjectSnapshot):
            return analysis_results[0]
        raise NotImplementedError("Direct generation from analysis_results is not supported in this workflow.")

    def export(self, snapshot: Any, output_path: Path) -> None:
        """Exports the ProjectSnapshot or a dictionary to a YAML file."""
        if isinstance(snapshot, ProjectSnapshot):
            data = snapshot.model_dump(mode="json", exclude_none=True)
        elif isinstance(snapshot, dict):
            data = snapshot
        else:
            raise TypeError("Unsupported snapshot type for YAML export")

        with open(output_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
