from pathlib import Path
from typing import Any, Dict, List
import yaml

from codesage.snapshot.base_generator import SnapshotGenerator
from codesage.snapshot.models import ProjectSnapshot


class YAMLGenerator(SnapshotGenerator):
    def generate(self, analysis_results: List[Dict[str, Any]]) -> ProjectSnapshot:
        # For the new flow, the builder creates the ProjectSnapshot directly.
        # This generator is now primarily for serialization.
        if len(analysis_results) == 1 and isinstance(analysis_results[0], ProjectSnapshot):
            return analysis_results[0]
        # Placeholder for legacy compatibility if needed
        raise NotImplementedError("Direct generation from analysis_results is not supported in this workflow.")

    def export(self, snapshot: ProjectSnapshot, output_path: Path, compat_modules_view: bool = False) -> None:
        data = snapshot.model_dump(mode="json", exclude_none=True)
        if compat_modules_view:
            data["modules"] = self._create_modules_view(snapshot)

        with open(output_path, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

    def _create_modules_view(self, snapshot: ProjectSnapshot) -> Dict[str, Any]:
        modules = {}
        for file_snapshot in snapshot.files:
            module_path = ".".join(file_snapshot.path.split("/")[:-1])
            if module_path not in modules:
                modules[module_path] = {
                    "num_classes": 0,
                    "num_functions": 0,
                    "files": [],
                    "risk": {
                        "max_risk_score": 0.0,
                        "high_risk_files": 0,
                    }
                }

            if file_snapshot.metrics:
                modules[module_path]["num_classes"] += file_snapshot.metrics.num_classes
                modules[module_path]["num_functions"] += file_snapshot.metrics.num_functions

            if file_snapshot.risk:
                if file_snapshot.risk.risk_score > modules[module_path]["risk"]["max_risk_score"]:
                    modules[module_path]["risk"]["max_risk_score"] = file_snapshot.risk.risk_score
                if file_snapshot.risk.level == "high":
                    modules[module_path]["risk"]["high_risk_files"] += 1

            modules[module_path]["files"].append(file_snapshot.path)
        return modules
