from click.testing import CliRunner
from pathlib import Path
import yaml
import json
from datetime import datetime, timedelta, timezone

from codesage.cli.main import main
from codesage.snapshot.models import ProjectSnapshot, SnapshotMetadata


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


def test_history_trend_cli(tmp_path: Path):
    runner = CliRunner()
    project_name = "trend-test"
    history_root = tmp_path / "history"
    history_root.mkdir()

    config_path = tmp_path / ".codesage.yaml"
    with config_path.open("w") as f:
        yaml.dump({"history": {"history_root": str(history_root)}}, f)

    # Create and save 3 snapshots
    for i in range(3):
        snapshot = create_test_snapshot(project_name, [])
        snap_path = tmp_path / f"snap_{i}.yaml"
        snap_path.write_text(yaml.safe_dump(snapshot.model_dump(mode='json')))
        commit_id = f"commit_{i}"

        # Manually create meta to control timestamp
        ts = (datetime.now(timezone.utc) - timedelta(days=2-i)).isoformat()

        runner.invoke(main, [
            'history-snapshot', '--snapshot', str(snap_path), '--project-name', project_name,
            '--commit', commit_id, '--config-file', str(config_path)
        ])

    # Generate trend report
    trend_path = tmp_path / "trend.json"
    result = runner.invoke(main, [
        'history-trend', '--project-name', project_name, '--output', str(trend_path),
        '--config-file', str(config_path)
    ])
    assert result.exit_code == 0

    with trend_path.open('r') as f:
        trend_data = json.load(f)

    assert len(trend_data['points']) == 3
    assert trend_data['points'][0]['snapshot_id'] == 'commit_0'
    assert trend_data['points'][2]['snapshot_id'] == 'commit_2'
