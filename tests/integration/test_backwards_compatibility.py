from pathlib import Path
from click.testing import CliRunner
from datetime import datetime, UTC
import yaml

from codesage.cli.main import main
from codesage.snapshot.models import ProjectSnapshot, SnapshotMetadata

def create_test_snapshot(tmp_path: Path, project_name: str) -> Path:
    snapshot = ProjectSnapshot(
        metadata=SnapshotMetadata(
            version="1.0",
            timestamp=datetime.now(UTC),
            project_name=project_name,
            file_count=0,
            total_size=0,
            tool_version="0.1.0",
            config_hash="abc",
        ),
        files=[],
        languages=[],
    )
    snapshot_path = tmp_path / f"{project_name}_snapshot.yaml"
    with snapshot_path.open("w") as f:
        yaml.dump(snapshot.model_dump(mode="json"), f)
    return snapshot_path

def test_legacy_snapshot_command(tmp_path: Path):
    """Test that the snapshot command still works without any new config."""
    runner = CliRunner()

    (tmp_path / "project").mkdir()
    (tmp_path / "project" / "file.py").write_text("print('hello')")

    result = runner.invoke(
        main,
        ["snapshot", "create", str(tmp_path / "project")],
    )

    assert result.exit_code == 0

def test_legacy_report_command(tmp_path: Path):
    """Test that the report command still works without any new config."""
    runner = CliRunner()

    snapshot_path = create_test_snapshot(tmp_path, "test-project")

    result = runner.invoke(
        main,
        ["report", "--input", str(snapshot_path)],
    )

    assert result.exit_code == 0
