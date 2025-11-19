import json
from pathlib import Path
from click.testing import CliRunner
from datetime import datetime, UTC
import yaml

from codesage.cli.main import main
from codesage.snapshot.models import ProjectSnapshot, SnapshotMetadata, FileSnapshot, FileRisk, Issue, IssueLocation

def create_test_snapshot(tmp_path: Path, project_name: str, high_risk_files: int = 0, error_issues: int = 0) -> Path:
    files = []
    if high_risk_files > 0:
        files.append(
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
                ] * error_issues,
            )
        )

    snapshot = ProjectSnapshot(
        metadata=SnapshotMetadata(
            version="1.0",
            timestamp=datetime.now(UTC),
            project_name=project_name,
            file_count=len(files),
            total_size=100,
            tool_version="0.1.0",
            config_hash="abc",
        ),
        files=files,
        languages=["python"],
    )
    snapshot_path = tmp_path / f"{project_name}_snapshot.yaml"
    with snapshot_path.open("w") as f:
        yaml.dump(snapshot.model_dump(mode="json"), f)
    return snapshot_path

def test_cli_flow_no_policy(tmp_path: Path):
    """Test a CLI run with no policy file works and logs 'no policy'."""
    runner = CliRunner()
    project_name = "test-project-no-policy"
    snapshot_path = create_test_snapshot(tmp_path, project_name)

    (tmp_path / ".codesage.yaml").write_text(f"""
audit:
  log_dir: "{tmp_path}/audit"
""")

    result = runner.invoke(
        main,
        ["--config", str(tmp_path / ".codesage.yaml"), "report", "--input", str(snapshot_path), "--ci-policy-strict"],
    )

    assert result.exit_code == 0

    audit_log = next((tmp_path / "audit").glob("*.log"))
    with audit_log.open("r") as f:
        log_entry = json.loads(f.read())
        assert log_entry["event_type"] == "cli.report"
        assert log_entry["project_name"] == project_name

def test_cli_flow_with_deny_policy(tmp_path: Path):
    """Test CLI run with valid policy enforces allow/deny."""
    runner = CliRunner()
    project_name = "test-project-deny-policy"
    snapshot_path = create_test_snapshot(tmp_path, project_name, high_risk_files=1, error_issues=1)

    policy_content = """
rules:
  - id: "block_on_high_risk"
    scope: "project"
    conditions:
      - field: "high_risk_files"
        op: ">"
        value: 0
    actions:
      - type: "suggest_block_ci"
"""
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(policy_content)

    (tmp_path / ".codesage.yaml").write_text(f"""
audit:
  log_dir: "{tmp_path}/audit"
policy:
  project_policy_path: "{policy_path}"
""")

    result = runner.invoke(
        main,
        ["--config", str(tmp_path / ".codesage.yaml"), "report", "--input", str(snapshot_path), "--ci-policy-strict"],
    )

    assert result.exit_code == 1
    assert "CI policy failed" in result.output

    audit_log = next((tmp_path / "audit").glob("*.log"))
    with audit_log.open("r") as f:
        log_entry = json.loads(f.read())
        assert log_entry["event_type"] == "cli.report"
        assert log_entry["project_name"] == project_name
