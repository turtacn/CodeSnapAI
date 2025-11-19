from codesage.org.models import OrgProjectHealth, OrgProjectRef
from codesage.web.org_api_models import ApiOrgProjectItem


def test_api_org_project_view_model():
    health = OrgProjectHealth(
        project=OrgProjectRef(
            id="p1", name="Proj 1", snapshot_path="s.yaml", tags=["a", "b"]
        ),
        health_score=80,
        risk_level="low",
        high_risk_files=1,
        total_issues=10,
        error_issues=1,
        has_recent_regression=False,
        open_governance_tasks=5,
        governance_completion_ratio=0.5,
    )
    api_model = ApiOrgProjectItem(
        id=health.project.id,
        name=health.project.name,
        tags=health.project.tags,
        health_score=health.health_score,
        risk_level=health.risk_level,
        high_risk_files=health.high_risk_files,
        total_issues=health.total_issues,
        has_recent_regression=health.has_recent_regression,
    )

    # This test is primarily for ensuring the model can be created.
    assert api_model.id == "p1"
    assert api_model.name == "Proj 1"
    assert api_model.health_score == 80
