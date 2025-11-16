from click.testing import CliRunner
from codesage.cli.main import main
from unittest.mock import patch, MagicMock
from codesage.snapshot.differ import SnapshotDiff, DependencyDiff

@patch('codesage.cli.commands.diff.SnapshotVersionManager')
@patch('codesage.cli.commands.diff.SnapshotDiffer')
def test_diff_command(mock_differ, mock_manager):
    """Test the diff command."""
    runner = CliRunner()
    manager_instance = mock_manager.return_value
    manager_instance.load_snapshot.return_value = MagicMock()

    differ_instance = mock_differ.return_value
    differ_instance.diff.return_value = SnapshotDiff(
        added_files=['a.py'],
        removed_files=['b.py'],
        modified_files=[],
        dependency_changes=DependencyDiff(added_edges=[], removed_edges=[])
    )

    result = runner.invoke(main, ['diff', 'v1', 'v2'])

    assert result.exit_code == 0
    assert "Added files: 1" in result.output
    assert "Removed files: 1" in result.output
