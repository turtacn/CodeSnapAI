from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import List, Optional

from codesage.config.web import WebConsoleConfig
from codesage.web.loader import load_snapshot, load_report, load_governance_plan
from codesage.config.loader import load_config
from codesage.config.org import OrgConfig
from codesage.org.aggregator import OrgAggregator
from codesage.web.api_models import (
    ApiProjectSummary,
    ApiFileListItem,
    ApiFileDetail,
    ApiGovernanceTask,
)
from codesage.web.org_api_models import ApiOrgProjectItem, ApiOrgReport
from codesage.governance.task_models import GovernancePlan
from codesage.jules.prompt_builder import JulesPromptConfig, build_prompt
from codesage.governance.jules_bridge import build_view_and_template_for_task
from codesage.report.generator import ReportGenerator

def create_app(config: WebConsoleConfig) -> "FastAPI":
    app = FastAPI()

    def find_task_in_plan(plan: GovernancePlan, task_id: str):
        for group in plan.groups:
            for task in group.tasks:
                if task.id == task_id:
                    return task
        return None

    @app.get("/api/project/summary", response_model=ApiProjectSummary)
    def get_project_summary():
        try:
            snapshot = load_snapshot(Path(config.snapshot_path))
            if config.report_path:
                report_summary, _ = load_report(Path(config.report_path))
            else:
                report_summary, _ = ReportGenerator.from_snapshot(snapshot)

            return ApiProjectSummary(
                project_name=snapshot.metadata.project_name,
                total_files=len(snapshot.files),
                languages=snapshot.languages,
                files_per_language=snapshot.language_stats,
                high_risk_files=report_summary.high_risk_files,
                total_issues=report_summary.total_issues,
            )
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Snapshot or report file not found")

    @app.get("/api/files", response_model=List[ApiFileListItem])
    def list_files(language: Optional[str] = None, risk_level: Optional[str] = None):
        try:
            snapshot = load_snapshot(Path(config.snapshot_path))
            if config.report_path:
                _, file_summaries = load_report(Path(config.report_path))
            else:
                _, file_summaries = ReportGenerator.from_snapshot(snapshot)

            results = []
            for file_summary in file_summaries:
                if language and file_summary.language != language:
                    continue
                if risk_level and file_summary.risk.level.lower() != risk_level.lower():
                    continue

                results.append(
                    ApiFileListItem(
                        path=file_summary.path,
                        language=file_summary.language,
                        risk_level=file_summary.risk.level,
                        risk_score=file_summary.risk.score,
                        issues_total=file_summary.issues_total,
                    )
                )
            return results
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Snapshot or report file not found")

    @app.get("/api/files/{file_path:path}", response_model=ApiFileDetail)
    def get_file_detail(file_path: str):
        try:
            snapshot = load_snapshot(Path(config.snapshot_path))
            file_snapshot = next((f for f in snapshot.files if f.path == file_path), None)
            if not file_snapshot:
                raise HTTPException(status_code=404, detail="File not found in snapshot")

            return ApiFileDetail(
                path=file_snapshot.path,
                language=file_snapshot.language,
                metrics=file_snapshot.metrics.dict(),
                risk=file_snapshot.risk.dict() if file_snapshot.risk else {},
                issues=[issue.dict() for issue in file_snapshot.issues],
            )
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Snapshot file not found")

    @app.get("/api/governance/plan", response_model=GovernancePlan)
    def get_governance_plan():
        try:
            return load_governance_plan(Path(config.governance_plan_path))
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Governance plan not found")

    @app.get("/api/governance/tasks/{task_id}", response_model=ApiGovernanceTask)
    def get_governance_task(task_id: str):
        try:
            plan = load_governance_plan(Path(config.governance_plan_path))
            task = find_task_in_plan(plan, task_id)
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            return ApiGovernanceTask(
                task_id=task.id,
                rule_id=task.rule_id,
                file_path=task.file_path,
                status=task.status,
                metadata=task.metadata,
            )
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Governance plan not found")

    @app.get("/api/governance/tasks/{task_id}/jules-prompt")
    def get_task_jules_prompt(task_id: str):
        try:
            snapshot = load_snapshot(Path(config.snapshot_path))
            plan = load_governance_plan(Path(config.governance_plan_path))
            task = find_task_in_plan(plan, task_id)
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            jules_config = JulesPromptConfig.default()
            view, template = build_view_and_template_for_task(task, snapshot, jules_config)
            prompt = build_prompt(view, template, jules_config)
            return {"task_id": task_id, "prompt": prompt}
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Snapshot or governance plan not found")

    @app.get("/api/org/projects", response_model=List[ApiOrgProjectItem])
    def list_org_projects():
        try:
            full_config = load_config(Path.cwd())
            org_config = OrgConfig.parse_obj(full_config.get("org", {}))
            if not org_config.projects:
                return []

            aggregator = OrgAggregator(org_config)
            overview = aggregator.aggregate()

            items = []
            for h in overview.projects:
                items.append(
                    ApiOrgProjectItem(
                        id=h.project.id,
                        name=h.project.name,
                        tags=h.project.tags,
                        health_score=h.health_score,
                        risk_level=h.risk_level,
                        high_risk_files=h.high_risk_files,
                        total_issues=h.total_issues,
                        has_recent_regression=h.has_recent_regression,
                    )
                )
            return items
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to load organization projects: {e}")

    @app.get("/api/org/report", response_model=ApiOrgReport)
    def get_org_report():
        try:
            full_config = load_config(Path.cwd())
            org_config = OrgConfig.parse_obj(full_config.get("org", {}))
            if not org_config.projects:
                raise HTTPException(status_code=404, detail="No projects configured for the organization.")

            aggregator = OrgAggregator(org_config)
            overview = aggregator.aggregate()

            items = [
                ApiOrgProjectItem(
                    id=h.project.id,
                    name=h.project.name,
                    tags=h.project.tags,
                    health_score=h.health_score,
                    risk_level=h.risk_level,
                    high_risk_files=h.high_risk_files,
                    total_issues=h.total_issues,
                    has_recent_regression=h.has_recent_regression,
                )
                for h in overview.projects
            ]

            return ApiOrgReport(
                total_projects=overview.total_projects,
                projects_with_regressions=overview.projects_with_regressions,
                avg_health_score=overview.avg_health_score,
                projects=items,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate organization report: {e}")

    # Serve the frontend
    ui_dir = Path(__file__).parent / "ui" / "build"
    if ui_dir.exists():
        app.mount("/", StaticFiles(directory=ui_dir, html=True), name="ui")

    return app
