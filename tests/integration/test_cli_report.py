from __future__ import annotations
import pytest
import yaml
from click.testing import CliRunner
from codesage.cli.main import main


@pytest.fixture
def snapshot_yaml(tmp_path):
    snapshot_data = {
        "metadata": {
            "version": "1.0",
            "timestamp": "2023-01-01T00:00:00",
            "project_name": "test",
            "file_count": 1,
            "total_size": 1024,
            "tool_version": "0.1.0",
            "config_hash": "abc"
        },
        "files": [
            {
                "path": "file1.py",
                "language": "python",
                "risk": {"risk_score": 0.8, "level": "high", "factors": []},
                "issues": [
                    {
                        "rule_id": "E001",
                        "severity": "error",
                        "message": "Error 1",
                        "location": {"file_path": "file1.py", "line": 10}
                    }
                ],
            }
        ],
    }
    snapshot_path = tmp_path / "snapshot.yaml"
    with open(snapshot_path, "w") as f:
        yaml.dump(snapshot_data, f)
    return snapshot_path


def test_cli_report_json_markdown_junit(snapshot_yaml, tmp_path):
    runner = CliRunner()
    json_path = tmp_path / "report.json"
    md_path = tmp_path / "report.md"
    junit_path = tmp_path / "report.junit.xml"

    result = runner.invoke(main, [
        "report",
        "--input", str(snapshot_yaml),
        "--out-json", str(json_path),
        "--out-md", str(md_path),
        "--out-junit", str(junit_path),
    ])

    assert result.exit_code == 0
    assert json_path.exists()
    assert md_path.exists()
    assert junit_path.exists()


def test_cli_report_ci_exit_code(snapshot_yaml):
    runner = CliRunner()

    result = runner.invoke(main, [
        "report",
        "--input", str(snapshot_yaml),
        "--ci-policy-strict",
    ])

    assert result.exit_code == 1
    assert "CI policy failed" in result.output
