from typing import List, Optional
import pytest
from datetime import datetime
from codesage.policy.dsl_models import PolicySet
from codesage.policy.engine import evaluate_project_policies, PolicyDecision
from codesage.snapshot.models import ProjectSnapshot, SnapshotMetadata, FileSnapshot, FileRisk, Issue, IssueLocation
from codesage.report.summary_models import ReportProjectSummary
from codesage.history.diff_models import ProjectDiffSummary
from codesage.history.regression_detector import RegressionWarning
from codesage.report.generator import ReportGenerator

@pytest.fixture
def high_risk_snapshot() -> ProjectSnapshot:
    return ProjectSnapshot(
        metadata=SnapshotMetadata(
            version="1.0",
            timestamp=datetime.now(),
            project_name="test-project",
            file_count=1,
            total_size=100,
            tool_version="0.1.0",
            config_hash="abc",
        ),
        files=[
            FileSnapshot(
                path="some_file.py",
                language="python",
                risk=FileRisk(risk_score=0.8, level="high", factors=[]),
                issues=[
                    Issue(
                        rule_id="some-rule",
                        severity="error",
                        message="Some error",
                        location=IssueLocation(file_path="some_file.py", line=10),
                    )
                ],
            )
        ],
        languages=["python"],
    )

@pytest.fixture
def high_risk_report(high_risk_snapshot: ProjectSnapshot) -> ReportProjectSummary:
    summary, _ = ReportGenerator.from_snapshot(high_risk_snapshot)
    return summary

def test_engine_applies_rule_on_high_risk_project(high_risk_snapshot: ProjectSnapshot, high_risk_report: ReportProjectSummary):
    policy_set = PolicySet.model_validate({
        "rules": [{
            "id": "high_risk_alert",
            "scope": "project",
            "conditions": [{
                "field": "high_risk_files",
                "op": ">",
                "value": 0
            }],
            "actions": [{
                "type": "raise_warning"
            }]
        }]
    })

    decisions = evaluate_project_policies(policy_set, high_risk_snapshot, high_risk_report, None, None)

    assert len(decisions) == 1
    decision = decisions[0]
    assert decision.rule_id == "high_risk_alert"
    assert decision.severity == "warning"

def test_engine_handles_regression_rule(high_risk_snapshot: ProjectSnapshot, high_risk_report: ReportProjectSummary):
    policy_set = PolicySet.model_validate({
        "rules": [{
            "id": "regression_alert",
            "scope": "project",
            "conditions": [{
                "field": "has_regression",
                "op": "==",
                "value": True
            }],
            "actions": [{
                "type": "suggest_block_ci"
            }]
        }]
    })

    regression_warning = RegressionWarning(
        id="high_risk_files_increase",
        from_snapshot_id="1",
        to_snapshot_id="2",
        severity="error",
        message="High risk files increased"
    )

    decisions = evaluate_project_policies(policy_set, high_risk_snapshot, high_risk_report, None, [regression_warning])

    assert len(decisions) == 1
    decision = decisions[0]
    assert decision.rule_id == "regression_alert"
    assert decision.severity == "error"
