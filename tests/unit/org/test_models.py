from codesage.org.models import OrgProjectHealth, OrgProjectRef


def test_org_project_health_fields():
    ref = OrgProjectRef(
        id="proj1",
        name="Project 1",
        tags=["python", "backend"],
        snapshot_path="/path/to/snapshot.yaml",
    )
    health = OrgProjectHealth(
        project=ref,
        health_score=85.5,
        risk_level="medium",
        high_risk_files=5,
        total_issues=20,
        error_issues=3,
        has_recent_regression=False,
        open_governance_tasks=2,
        governance_completion_ratio=0.8,
    )
    assert health.project.name == "Project 1"
    assert health.health_score == 85.5
    assert health.risk_level == "medium"
    assert not health.has_recent_regression
