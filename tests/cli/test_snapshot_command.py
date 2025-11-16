from click.testing import CliRunner
from codesage.cli.main import main
from unittest.mock import patch, MagicMock
import os
import json

@patch('codesage.cli.commands.snapshot.analyze')
@patch('codesage.cli.commands.snapshot.SnapshotVersionManager')
def test_snapshot_create(mock_manager, mock_analyze, tmp_path):
    """Test snapshot creation."""
    runner = CliRunner()
    instance = mock_manager.return_value
    instance.save_snapshot.return_value = ".codesage/snapshots/v1.json"

    # Create a dummy snapshot to be returned by the mocked analyze command
    from codesage.snapshot.models import ProjectSnapshot, SnapshotMetadata, DependencyGraph
    from codesage import __version__ as tool_version
    dummy_snapshot = ProjectSnapshot(
        metadata=SnapshotMetadata(
            version="v1", timestamp="2023-01-01T12:00:00", tool_version=tool_version, config_hash="dummy"
        ),
        files=[], global_metrics={}, dependency_graph=DependencyGraph(), detected_patterns=[], issues=[]
    )

    def side_effect(path, language, exclude, output, format, no_progress):
        with open(output, 'w') as f:
            f.write(dummy_snapshot.model_dump_json())
    mock_analyze.side_effect = side_effect

    result = runner.invoke(main, ['snapshot', 'create', '--path', '.'])

    assert result.exit_code == 0
    assert "Snapshot 'v1' saved to .codesage/snapshots/v1.json" in result.output

@patch('click.echo')
@patch('codesage.cli.commands.snapshot.SnapshotVersionManager')
def test_snapshot_list(mock_manager, mock_echo):
    """Test listing snapshots."""
    runner = CliRunner()
    instance = mock_manager.return_value
    instance.list_snapshots.return_value = [
        {'version': 'v1', 'timestamp': '2023-01-01T12:00:00'},
        {'version': 'v2', 'timestamp': '2023-01-02T12:00:00'},
    ]

    result = runner.invoke(main, ['snapshot', 'list'])

    assert result.exit_code == 0

    table = mock_echo.call_args.args[0]
    assert "Version" in [c.header for c in table.columns]
    assert "Timestamp" in [c.header for c in table.columns]
