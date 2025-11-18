import pytest
import yaml
from pathlib import Path
from click.testing import CliRunner
from codesage.cli.main import main

runner = CliRunner()
FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "complex_project"


def test_cli_snapshot_export_with_issues(tmp_path):
    output_file = tmp_path / "snapshot.yaml"
    result = runner.invoke(
        main,
        [
            "snapshot",
            "create",
            str(FIXTURE_DIR),
            "--format",
            "python-semantic-digest",
            "--output",
            str(output_file),
        ],
    )

    assert result.exit_code == 0
    assert output_file.exists()

    with open(output_file, "r") as f:
        data = yaml.safe_load(f)

    assert "issues_summary" in data
    assert data["issues_summary"]["total_issues"] > 0
    assert "files" in data

    issue_found_in_file = False
    for file in data["files"]:
        if "issues" in file and len(file["issues"]) > 0:
            issue_found_in_file = True
            break

    assert issue_found_in_file, "Expected to find issues in at least one file"
