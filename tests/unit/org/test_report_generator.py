from codesage.org.models import OrgGovernanceOverview, OrgProjectHealth, OrgProjectRef
from codesage.org.report_generator import (
    render_org_report_json,
    render_org_report_markdown,
)
import json


def test_org_report_json_structure():
    overview = OrgGovernanceOverview(
        projects=[
            OrgProjectHealth(
                project=OrgProjectRef(id="p1", name="Proj 1", snapshot_path="s.yaml"),
                health_score=80,
                risk_level="low",
                high_risk_files=1,
                total_issues=10,
                error_issues=1,
                has_recent_regression=False,
                open_governance_tasks=5,
                governance_completion_ratio=0.5,
            )
        ],
        total_projects=1,
        projects_with_regressions=0,
        avg_health_score=80.0,
    )
    report = render_org_report_json(overview)
    data = json.loads(report)
    assert data["total_projects"] == 1
    assert data["projects"][0]["name"] == "Proj 1"


def test_org_report_markdown_contains_project_table():
    overview = OrgGovernanceOverview(
        projects=[
            OrgProjectHealth(
                project=OrgProjectRef(id="p1", name="Proj 1", snapshot_path="s.yaml"),
                health_score=80,
                risk_level="low",
                high_risk_files=1,
                total_issues=10,
                error_issues=1,
                has_recent_regression=False,
                open_governance_tasks=5,
                governance_completion_ratio=0.5,
            )
        ],
        total_projects=1,
        projects_with_regressions=0,
        avg_health_score=80.0,
    )
    report = render_org_report_markdown(overview)
    assert "| Project | Health Score | Risk Level | Error Issues | Open Tasks | Regressions |" in report
    assert "| Proj 1 | 80.00 | Low | 1 | 5 | ✅ |" in report
