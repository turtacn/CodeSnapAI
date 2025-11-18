from __future__ import annotations
import json
from typing import List
from codesage.report.summary_models import ReportProjectSummary, ReportFileSummary


def render_json(project_summary: ReportProjectSummary, files: List[ReportFileSummary]) -> str:
    report_data = {
        "project": project_summary.dict(),
        "files": [file.dict() for file in files],
    }
    return json.dumps(report_data, indent=2)
