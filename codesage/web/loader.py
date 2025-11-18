from pathlib import Path
from typing import Optional, Tuple, List
import yaml
import json

from codesage.snapshot.models import ProjectSnapshot
from codesage.report.summary_models import ReportProjectSummary, ReportFileSummary
from codesage.governance.task_models import GovernancePlan

_snapshot_cache: Optional[ProjectSnapshot] = None
_report_cache: Optional[Tuple[ReportProjectSummary, List[ReportFileSummary]]] = None
_plan_cache: Optional[GovernancePlan] = None

def load_snapshot(snapshot_path: Path) -> ProjectSnapshot:
    global _snapshot_cache
    if _snapshot_cache is None:
        data = yaml.safe_load(snapshot_path.read_text(encoding="utf-8"))
        _snapshot_cache = ProjectSnapshot.parse_obj(data)
    return _snapshot_cache

def load_report(report_path: Path) -> Tuple[ReportProjectSummary, List[ReportFileSummary]]:
    global _report_cache
    if _report_cache is None:
        data = json.loads(report_path.read_text(encoding="utf-8"))
        project_summary = ReportProjectSummary.parse_obj(data['project_summary'])
        file_summaries = [ReportFileSummary.parse_obj(item) for item in data['files']]
        _report_cache = (project_summary, file_summaries)
    return _report_cache

def load_governance_plan(plan_path: Path) -> GovernancePlan:
    global _plan_cache
    if _plan_cache is None:
        data = yaml.safe_load(plan_path.read_text(encoding="utf-8"))
        _plan_cache = GovernancePlan.parse_obj(data)
    return _plan_cache

def reload_all():
    global _snapshot_cache, _report_cache, _plan_cache
    _snapshot_cache = None
    _report_cache = None
    _plan_cache = None
