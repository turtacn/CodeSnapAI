from pathlib import Path
import json
from codesage.integrations.file_export import export_policy_decisions
from codesage.policy.engine import PolicyDecision
from codesage.policy.dsl_models import PolicyAction

def test_file_export_writes_decision_files(tmp_path: Path):
    decisions = [
        PolicyDecision(
            rule_id="test-rule",
            scope="project",
            target="test-project",
            severity="error",
            actions=[PolicyAction(type="suggest_block_ci")],
            reason="Test reason"
        )
    ]

    export_dir = tmp_path / "export"
    export_policy_decisions(decisions, export_dir)

    export_file = next(export_dir.glob("*.json"))
    with export_file.open("r") as f:
        data = json.load(f)
        assert len(data) == 1
        decision_data = data[0]
        assert decision_data["rule_id"] == "test-rule"
        assert decision_data["severity"] == "error"
