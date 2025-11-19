from click.testing import CliRunner
from pathlib import Path
import yaml
import json

from codesage.cli.main import main
from tests.unit.org.test_aggregator import mock_project_artifacts


def test_org_report_cli(mock_project_artifacts, tmp_path: Path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    org_config_path = config_dir / ".codesage.yaml"
    org_config = {
        "org": {
            "projects": [
                {
                    "id": f"proj{i}",
                    "name": f"proj{i}",
                    "tags": ["python"],
                    "snapshot_path": str(mock_project_artifacts[f"proj{i}"]["snapshot"]),
                    "report_path": str(mock_project_artifacts[f"proj{i}"]["report"]),
                    "governance_plan_path": str(mock_project_artifacts[f"proj{i}"]["governance"]),
                }
                for i in range(1, 3)
            ],
            "health_weights": {
                "risk_weight": 2.0,
                "issues_weight": 0.1,
                "regression_weight": 15.0,
                "governance_progress_weight": 10.0,
            },
        }
    }
    org_config_path.write_text(yaml.dump(org_config))

    out_json_path = tmp_path / "org_report.json"
    out_md_path = tmp_path / "org_report.md"

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "org-report",
            "--config",
            str(org_config_path),
            "--out-json",
            str(out_json_path),
            "--out-md",
            str(out_md_path),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert out_json_path.exists()
    assert out_md_path.exists()

    json_report = json.loads(out_json_path.read_text())
    assert json_report["total_projects"] == 2
    assert len(json_report["projects"]) == 2

    md_report = out_md_path.read_text()
    assert "Organization Governance Report" in md_report
    assert "proj1" in md_report
    assert "proj2" in md_report
