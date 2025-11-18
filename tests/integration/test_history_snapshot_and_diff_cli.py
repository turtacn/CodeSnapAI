from click.testing import CliRunner
from pathlib import Path
import yaml
from datetime import datetime, timezone

from codesage.cli.main import main
from codesage.snapshot.models import ProjectSnapshot, SnapshotMetadata, FileSnapshot, FileRisk


def create_test_snapshot(project_name, files):
    return ProjectSnapshot(
        metadata=SnapshotMetadata(
            version="1.0",
            timestamp=datetime.now(timezone.utc),
            project_name=project_name,
            file_count=len(files),
            total_size=100,
            tool_version="0.1.0",
            config_hash="dummy_hash"
        ),
        files=files
    )


def test_history_snapshot_and_diff_cli(tmp_path: Path):
    runner = CliRunner()
    project_name = "cli-test"
    history_root = tmp_path / "history"
    history_root.mkdir()

    config_path = tmp_path / ".codesage.yaml"
    with config_path.open("w") as f:
        yaml.dump({"history": {"history_root": str(history_root)}}, f)


    # Create two snapshots
    snapshot_v1 = create_test_snapshot(project_name, [
        FileSnapshot(path="a.py", language="python", risk=FileRisk(risk_score=0.2, level="low"))
    ])
    snapshot_v2 = create_test_snapshot(project_name, [
        FileSnapshot(path="a.py", language="python", risk=FileRisk(risk_score=0.8, level="high"))
    ])

    snap1_path = tmp_path / "snap1.yaml"
    snap2_path = tmp_path / "snap2.yaml"
    snap1_path.write_text(yaml.safe_dump(snapshot_v1.model_dump(mode='json')))
    snap2_path.write_text(yaml.safe_dump(snapshot_v2.model_dump(mode='json')))

    # Save snapshots to history
    result1 = runner.invoke(main, [
        'history-snapshot', '--snapshot', str(snap1_path), '--project-name', project_name, '--commit', 'abc',
        '--config-file', str(config_path)
    ], catch_exceptions=False)
    assert result1.exit_code == 0

    result2 = runner.invoke(main, [
        'history-snapshot', '--snapshot', str(snap2_path), '--project-name', project_name, '--commit', 'def',
        '--config-file', str(config_path)
    ])
    assert result2.exit_code == 0

    # Diff the snapshots
    diff_path = tmp_path / "diff.yaml"
    result_diff = runner.invoke(main, [
        'history-diff', '--project-name', project_name, '--from-id', 'abc', '--to-id', 'def', '--output', str(diff_path),
        '--config-file', str(config_path)
    ])
    assert result_diff.exit_code == 0

    with diff_path.open('r') as f:
        diff_data = yaml.safe_load(f)

    assert diff_data['project_diff']['high_risk_files_delta'] == 1
    assert diff_data['file_diffs'][0]['path'] == 'a.py'
    assert diff_data['file_diffs'][0]['status'] == 'modified'
