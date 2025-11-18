from pathlib import Path
from click.testing import CliRunner
from codesage.cli.main import main
from codesage.utils.file_utils import read_yaml_file

def test_cli_governance_plan_export(tmp_path: Path):
    runner = CliRunner()

    snapshot_path = Path(__file__).parent.parent.parent / "fixtures" / "snapshot_samples" / "governance_test_snapshot.yaml"
    output_path = tmp_path / "governance_plan.yaml"

    result = runner.invoke(
        main,
        [
            "governance-plan",
            "--input",
            str(snapshot_path),
            "--output",
            str(output_path),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert output_path.exists()

    plan_data = read_yaml_file(output_path)
    assert plan_data["project_name"] == "integration_test_project"
    assert len(plan_data["groups"]) > 0
