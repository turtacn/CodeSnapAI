import pytest
from pathlib import Path
import yaml
import json
from datetime import datetime

from codesage.config.org import OrgConfig, OrgProjectRefConfig
from codesage.org. aggregator import OrgAggregator
from codesage.snapshot.models import (
    ProjectSnapshot,
    SnapshotMetadata,
    FileSnapshot,
    FileMetrics,
    ProjectRiskSummary,
    ProjectIssuesSummary,
    FileRisk,
)
from codesage.report.summary_models import ReportProjectSummary
from codesage.governance.task_models import GovernancePlan, GovernanceTask, GovernanceTaskGroup


@pytest.fixture
def mock_project_artifacts(tmp_path: Path) -> dict:
    projects = {}
    for i in range(1, 3):
        proj_dir = tmp_path / f"proj{i}"
        proj_dir.mkdir()

        # Create snapshot
        snapshot = ProjectSnapshot(
            metadata=SnapshotMetadata(
                project_name=f"proj{i}",
                version="1.0",
                timestamp=datetime.now(),
                file_count=2,
                total_size=100,
                tool_version="0.1.0",
                config_hash="abc",
            ),
            files=[
                FileSnapshot(
                    path=f"file{j}.py",
                    language="python",
                    metrics=FileMetrics(
                        lines_of_code=10,
                        num_functions=1,
                        num_types=0,
                        language_specific={"complexity": j},
                    ),
                    risk=FileRisk(
                        risk_score=j * 0.1,
                        level="high" if j == 1 else "low",
                        factors=[],
                    ),
                )
                for j in range(1, 3)
            ],
            risk_summary=ProjectRiskSummary(
                avg_risk=0.15,
                high_risk_files=1,
                medium_risk_files=0,
                low_risk_files=1,
            ),
            language_stats={"files_per_language": {"python": 2}},
        )
        snapshot_path = proj_dir / "snapshot.yaml"
        snapshot_path.write_text(yaml.dump(snapshot.model_dump()))

        # Create report
        report = {
            "summary": ReportProjectSummary(
                project_name=f"proj{i}",
                total_files=2,
                high_risk_files=1,
                medium_risk_files=0,
                low_risk_files=1,
                total_issues=i,
                error_issues=i,
                warning_issues=0,
                info_issues=0,
                top_rules=["rule1"],
                top_risky_files=["file1.py"],
                languages=["python"],
                files_per_language={"python": 2},
                risk_level="high",
            ).model_dump()
        }
        report_path = proj_dir / "report.json"
        report_path.write_text(json.dumps(report))

        # Create governance plan
        plan = GovernancePlan(
            project_name=f"proj{i}",
            created_at="2025-11-18T18:58:32.821938",
            summary={},
            groups=[
                GovernanceTaskGroup(
                    id="default",
                    name="Default Group",
                    group_by="default",
                    tasks=[
                        GovernanceTask(
                            id=f"task{k}",
                            project_name=f"proj{i}",
                            file_path=f"file{k}.py",
                            language="python",
                            rule_id="rule1",
                            description="A task",
                            priority=1,
                            risk_level="high",
                            status="done" if k == 1 else "pending",
                        )
                        for k in range(1, 3)
                    ],
                )
            ],
        )
        plan_path = proj_dir / "governance.yaml"
        plan_path.write_text(yaml.dump(plan.model_dump()))

        projects[f"proj{i}"] = {
            "snapshot": snapshot_path,
            "report": report_path,
            "governance": plan_path,
        }
    return projects


def test_aggregator_merges_multiple_projects(mock_project_artifacts, tmp_path):
    proj_configs = [
        OrgProjectRefConfig(
            id=f"proj{i}",
            name=f"proj{i}",
            snapshot_path=str(mock_project_artifacts[f"proj{i}"]["snapshot"]),
            report_path=str(mock_project_artifacts[f"proj{i}"]["report"]),
            governance_plan_path=str(mock_project_artifacts[f"proj{i}"]["governance"]),
        )
        for i in range(1, 3)
    ]
    org_config = OrgConfig(projects=proj_configs, health_weights=OrgConfig.default().health_weights)

    aggregator = OrgAggregator(org_config)
    overview = aggregator.aggregate()

    assert overview.total_projects == 2
    assert len(overview.projects) == 2
    assert overview.projects[0].project.name == "proj2"  # Lower error issues, higher score
    assert overview.projects[1].project.name == "proj1"


def test_health_scoring_combines_metrics(mock_project_artifacts):
    proj_configs = [
        OrgProjectRefConfig(
            id="proj1",
            name="proj1",
            snapshot_path=str(mock_project_artifacts["proj1"]["snapshot"]),
            report_path=str(mock_project_artifacts["proj1"]["report"]),
            governance_plan_path=str(mock_project_artifacts["proj1"]["governance"]),
        )
    ]

    # High risk weight
    org_config = OrgConfig(
        projects=proj_configs,
        health_weights={"risk_weight": 50.0, "issues_weight": 0.1, "regression_weight": 10.0, "governance_progress_weight": 10.0},
    )
    aggregator = OrgAggregator(org_config)
    overview = aggregator.aggregate()
    score1 = overview.projects[0].health_score

    # High issues weight
    org_config.health_weights = {"risk_weight": 1.0, "issues_weight": 50.0, "regression_weight": 10.0, "governance_progress_weight": 10.0}
    aggregator = OrgAggregator(org_config)
    overview = aggregator.aggregate()
    score2 = overview.projects[0].health_score

    assert score1 != score2
