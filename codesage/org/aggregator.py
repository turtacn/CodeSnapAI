from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Tuple

from codesage.config.history import HistoryConfig
from codesage.config.org import OrgConfig
from codesage.governance.task_models import GovernancePlan
from codesage.history.diff_engine import diff_project_snapshots
from codesage.history.diff_models import ProjectDiffSummary
from codesage.history.regression_detector import RegressionWarning, detect_regressions
from codesage.history.trend_builder import build_trend_series
from codesage.org.models import OrgGovernanceOverview, OrgProjectHealth, OrgProjectRef
from codesage.report.generator import ReportGenerator
from codesage.report.summary_models import ReportProjectSummary
from codesage.snapshot.models import ProjectSnapshot
from codesage.utils.file_utils import read_json_file, read_yaml_file

logger = logging.getLogger(__name__)


class OrgAggregator:
    def __init__(self, org_config: OrgConfig) -> None:
        self._config = org_config

    def aggregate(self) -> OrgGovernanceOverview:
        project_healths: List[OrgProjectHealth] = []

        for proj_cfg in self._config.projects:
            try:
                ref = OrgProjectRef(
                    id=proj_cfg.id,
                    name=proj_cfg.name,
                    tags=proj_cfg.tags or [],
                    snapshot_path=proj_cfg.snapshot_path,
                    report_path=proj_cfg.report_path,
                    history_root=proj_cfg.history_root,
                    governance_plan_path=proj_cfg.governance_plan_path,
                )
                health = self._compute_project_health(ref)
                project_healths.append(health)
            except Exception:
                logger.warning(f"Failed to aggregate data for project '{proj_cfg.name}'. Skipping.", exc_info=True)

        total_projects = len(project_healths)
        projects_with_regressions = sum(1 for h in project_healths if h.has_recent_regression)
        avg_health_score = (
            sum(h.health_score for h in project_healths) / total_projects if total_projects else 0.0
        )

        overview = OrgGovernanceOverview(
            projects=sorted(project_healths, key=lambda p: p.health_score),
            total_projects=total_projects,
            projects_with_regressions=projects_with_regressions,
            avg_health_score=avg_health_score,
        )
        return overview

    def _load_artifacts(
        self, ref: OrgProjectRef
    ) -> Tuple[
        ProjectSnapshot,
        ReportProjectSummary,
        List[RegressionWarning],
        GovernancePlan | None,
    ]:
        snapshot = ProjectSnapshot.parse_obj(read_yaml_file(Path(ref.snapshot_path)))

        report_summary = None
        if ref.report_path and Path(ref.report_path).exists():
            report_summary_dict = read_json_file(Path(ref.report_path))
            report_summary = ReportProjectSummary.parse_obj(report_summary_dict["summary"])

        if not report_summary:
            logger.info(f"No report found for {ref.name}, generating one from snapshot.")
            generator = ReportGenerator.from_snapshot(snapshot, Path.cwd())
            report_summary = generator.get_summary()

        regressions = []
        if ref.history_root and Path(ref.history_root).exists():
            trend = build_trend_series(Path(ref.history_root), snapshot.metadata.project_name)
            if len(trend.points) >= 2:
                latest_snapshot = trend.points[-1].snapshot
                previous_snapshot = trend.points[-2].snapshot
                diff, _ = diff_project_snapshots(
                    previous_snapshot,
                    latest_snapshot,
                    trend.points[-2].snapshot_id,
                    trend.points[-1].snapshot_id,
                )
                history_config = HistoryConfig.default()
                regressions = detect_regressions(diff, history_config)

        governance_plan = None
        if ref.governance_plan_path and Path(ref.governance_plan_path).exists():
            governance_plan = GovernancePlan.parse_obj(read_yaml_file(Path(ref.governance_plan_path)))

        return snapshot, report_summary, regressions, governance_plan

    def _compute_project_health(self, ref: OrgProjectRef) -> OrgProjectHealth:
        snapshot, report_summary, regressions, plan = self._load_artifacts(ref)

        high_risk_files = report_summary.high_risk_files
        total_issues = report_summary.total_issues
        error_issues = report_summary.error_issues
        has_recent_regression = bool(regressions)

        open_tasks = 0
        completion_ratio = 0.0
        if plan:
            all_tasks = [t for g in plan.groups for t in g.tasks]
            total_tasks = len(all_tasks)
            if total_tasks > 0:
                done_tasks = sum(1 for t in all_tasks if t.status == "done")
                open_tasks = total_tasks - done_tasks
                completion_ratio = done_tasks / total_tasks

        w = self._config.health_weights
        health_score = max(
            0.0,
            100.0
            - w.get("risk_weight", 1.0) * high_risk_files
            - w.get("issues_weight", 0.1) * error_issues
            - w.get("regression_weight", 10.0) * (1 if has_recent_regression else 0)
            + w.get("governance_progress_weight", 10.0) * completion_ratio,
        )

        risk_level = "low"
        if snapshot.risk_summary:
            if snapshot.risk_summary.avg_risk > 0.7:
                risk_level = "high"
            elif snapshot.risk_summary.avg_risk > 0.4:
                risk_level = "medium"

        return OrgProjectHealth(
            project=ref,
            health_score=round(health_score, 2),
            risk_level=risk_level,
            high_risk_files=high_risk_files,
            total_issues=total_issues,
            error_issues=error_issues,
            has_recent_regression=has_recent_regression,
            open_governance_tasks=open_tasks,
            governance_completion_ratio=completion_ratio,
        )
