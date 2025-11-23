import json
from .base import BaseReporter
from codesage.snapshot.models import ProjectSnapshot

class JsonReporter(BaseReporter):
    def __init__(self, output_path: str = "report.json"):
        self.output_path = output_path

    def report(self, snapshot: ProjectSnapshot) -> None:
        with open(self.output_path, "w") as f:
            f.write(snapshot.model_dump_json(indent=2))
        print(f"JSON report saved to {self.output_path}")
