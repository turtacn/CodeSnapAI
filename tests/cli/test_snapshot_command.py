from click.testing import CliRunner
from codesage.cli.main import main
from unittest.mock import patch, MagicMock

@patch('codesage.cli.commands.snapshot.SnapshotVersionManager')
def test_snapshot_create(mock_manager):
    """Test snapshot creation."""
    runner = CliRunner()
    instance = mock_manager.return_value
    instance.save_snapshot.return_value = ".codesage/snapshots/v1.json"

    with runner.isolated_filesystem():
        # Create a dummy directory to snapshot
        import os
        os.makedirs("test_project")

        result = runner.invoke(main, ['snapshot', 'create', 'test_project'])

        assert result.exit_code == 0
        assert "Snapshot created at .codesage/snapshots/v1.json" in result.output

@patch('codesage.cli.commands.snapshot.SnapshotVersionManager')
def test_snapshot_list(mock_manager):
    """Test listing snapshots."""
    runner = CliRunner()
    instance = mock_manager.return_value
    instance.list_snapshots.return_value = [
        {'version': 'v1', 'timestamp': '2023-01-01T12:00:00'},
        {'version': 'v2', 'timestamp': '2023-01-02T12:00:00'},
    ]

    result = runner.invoke(main, ['snapshot', 'list'])

    assert result.exit_code == 0
    assert "v1" in result.output
    assert "v2" in result.output
