from click.testing import CliRunner
from codesage.cli.main import main
import os
from unittest.mock import patch

@patch('click.echo')
def test_analyze_single_file(mock_echo, tmp_path):
    """Test analyzing a single file."""
    runner = CliRunner()
    test_file = tmp_path / "test.py"
    test_file.write_text("def hello():\\n    print('hello')")

    result = runner.invoke(main, ['analyze', str(test_file), '--no-progress'])

    assert result.exit_code == 0

    # Check the titles and table headers from the echo calls
    assert "Analysis Summary" in mock_echo.call_args_list[0].args[0]
    summary_table = mock_echo.call_args_list[1].args[0]
    assert "Metric" in [c.header for c in summary_table.columns]

    assert "Complexity Hotspots" in mock_echo.call_args_list[2].args[0]
    hotspots_table = mock_echo.call_args_list[3].args[0]
    assert "Function" in [c.header for c in hotspots_table.columns]

@patch('click.echo')
def test_analyze_directory(mock_echo, tmp_path):
    """Test analyzing a directory."""
    runner = CliRunner()
    (tmp_path / "test1.py").write_text("def func1(): pass")
    (tmp_path / "test2.py").write_text("def func2(): pass")

    result = runner.invoke(main, ['analyze', str(tmp_path), '--no-progress'])

    assert result.exit_code == 0
    assert "Analysis Summary" in mock_echo.call_args_list[0].args[0]
    summary_table = mock_echo.call_args_list[1].args[0]
    assert "Metric" in [c.header for c in summary_table.columns]

def test_analyze_invalid_path():
    """Test analyzing an invalid path."""
    runner = CliRunner()
    result = runner.invoke(main, ['analyze', 'nonexistent/path'])

    assert result.exit_code != 0
    assert "Path 'nonexistent/path' does not exist" in result.output
