from click.testing import CliRunner
from codesage.cli.main import main
import yaml
import pytest

@pytest.fixture
def snapshot_with_issues_file(tmp_path):
    p = tmp_path / "test.py"
    p.write_text("print('hello')\n" * 20)
    snapshot_data = {
        "metadata": {
            "project_name": "test-project",
            "version": "1.0",
            "timestamp": "2023-01-01T00:00:00.000000",
            "file_count": 1,
            "total_size": 0,
            "tool_version": "0.1.0",
            "config_hash": "abc",
        },
        "files": [
            {
                "path": str(p),
                "language": "python",
                "issues": [
                    {
                        "rule_id": "test-rule",
                        "severity": "warning",
                        "message": "This is a test issue",
                        "location": {"file_path": str(p), "line": 10},
                    }
                ],
            }
        ],
    }
    snapshot_file = tmp_path / "snapshot.yaml"
    with open(snapshot_file, "w") as f:
        yaml.dump(snapshot_data, f)
    return snapshot_file


def test_cli_llm_suggest_dummy(snapshot_with_issues_file, tmp_path):
    output_file = tmp_path / "enriched_snapshot.yaml"
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "llm-suggest",
            "--input",
            str(snapshot_with_issues_file),
            "--output",
            str(output_file),
            "--provider",
            "dummy",
        ],
    )

    assert result.exit_code == 0
    assert output_file.exists()

    with open(output_file, "r") as f:
        enriched_snapshot = yaml.safe_load(f)

    issue = enriched_snapshot["files"][0]["issues"][0]
    assert issue["llm_status"] == "succeeded"
    assert issue["llm_fix_hint"]
    assert enriched_snapshot["llm_stats"]["total_requests"] == 1
