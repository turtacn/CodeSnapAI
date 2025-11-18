from pathlib import Path
import yaml
from click.testing import CliRunner
from codesage.cli.commands.snapshot import snapshot

def test_cli_python_snapshot(tmp_path):
    # Create a dummy project structure
    project_path = tmp_path / "my_project"
    project_path.mkdir()
    (project_path / "main.py").write_text("def main():\n    pass")

    runner = CliRunner()
    output_path = tmp_path / "snapshot.yaml"
    result = runner.invoke(
        snapshot,
        [
            "create",
            str(project_path),
            "--format",
            "python-semantic-digest",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert output_path.exists()

    with open(output_path, "r") as f:
        data = yaml.safe_load(f)

    assert "metadata" in data
    assert data["metadata"]["project_name"] == "my_project"
    assert len(data["files"]) == 1
    assert data["files"][0]["metrics"]["num_functions"] == 1
