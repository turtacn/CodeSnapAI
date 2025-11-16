from click.testing import CliRunner
from codesage.cli.main import main
from unittest.mock import patch, MagicMock
from codesage.snapshot.differ import SnapshotDiff, DependencyDiff, FileChange

@patch('click.echo')
@patch('codesage.cli.commands.diff.SnapshotVersionManager')
@patch('codesage.cli.commands.diff.SnapshotDiffer')
def test_diff_command(mock_differ, mock_manager, mock_echo):
    """Test the diff command."""
    runner = CliRunner()
    manager_instance = mock_manager.return_value
    manager_instance.load_snapshot.return_value = MagicMock()

    differ_instance = mock_differ.return_value
    differ_instance.diff.return_value = SnapshotDiff(
        added_files=['a.py'],
        removed_files=['b.py'],
        modified_files=[FileChange(path='c.py', complexity_delta=2)],
        dependency_changes=DependencyDiff(added_edges=[], removed_edges=[])
    )

    result = runner.invoke(main, ['diff', 'v1', 'v2'])

    assert result.exit_code == 0

    # Check the contents of the echo calls
    assert "Comparing v1 and v2" in mock_echo.call_args_list[0].args[0]
    summary_table = mock_echo.call_args_list[1].args[0]
    assert "Metric" in [c.header for c in summary_table.columns]

    assert "Added Files" in mock_echo.call_args_list[2].args[0]
    assert "+ a.py" in mock_echo.call_args_list[3].args[0]

    assert "Removed Files" in mock_echo.call_args_list[4].args[0]
    assert "- b.py" in mock_echo.call_args_list[5].args[0]

    assert "Modified Files" in mock_echo.call_args_list[6].args[0]
    modified_table = mock_echo.call_args_list[7].args[0]
    assert "File" in [c.header for c in modified_table.columns]
