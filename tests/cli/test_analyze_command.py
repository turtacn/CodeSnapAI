from click.testing import CliRunner
from codesage.cli.main import main
import os

def test_analyze_single_file(tmp_path):
    """Test analyzing a single file."""
    runner = CliRunner()
    test_file = tmp_path / "test.py"
    test_file.write_text("def hello():\n    print('hello')")

    result = runner.invoke(main, ['analyze', str(test_file)])

    assert result.exit_code == 0
    assert "File:" in result.output
    assert "test.py" in result.output
    assert "Functions: 1" in result.output

def test_analyze_directory(tmp_path):
    """Test analyzing a directory."""
    runner = CliRunner()
    (tmp_path / "test1.py").write_text("def func1(): pass")
    (tmp_path / "test2.py").write_text("def func2(): pass")

    result = runner.invoke(main, ['analyze', str(tmp_path)])

    assert result.exit_code == 0
    assert "test1.py" in result.output
    assert "test2.py" in result.output

def test_analyze_invalid_path():
    """Test analyzing an invalid path."""
    runner = CliRunner()
    result = runner.invoke(main, ['analyze', 'nonexistent/path'])

    assert result.exit_code != 0
    assert "Path 'nonexistent/path' does not exist" in result.output
