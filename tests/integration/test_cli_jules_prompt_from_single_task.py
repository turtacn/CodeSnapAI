import pytest
from click.testing import CliRunner
from codesage.cli.main import main
import yaml

@pytest.fixture
def single_task_file(tmp_path):
    """Creates a dummy single_task.yaml file."""
    task_content = {
        "id": "test.py:PY_MISSING_TYPE_HINTS:5",
        "rule_id": "PY_MISSING_TYPE_HINTS",
        "language": "python",
        "description": "Missing type hints",
        "file_path": "test.py",
        "priority": 1,
        "risk_level": "low",
        "status": "pending",
        "metadata": {"start_line": 5, "end_line": 8},
    }
    task_file = tmp_path / "single_task.yaml"
    with open(task_file, "w") as f:
        yaml.dump(task_content, f)
    return str(task_file)

def test_cli_jules_prompt_from_single_task(single_task_file):
    """
    Tests the `codesage jules-prompt` command with a single task file.
    """
    runner = CliRunner()
    result = runner.invoke(main, ["jules-prompt", "--task", single_task_file])

    assert result.exit_code == 0
    assert "TASK: Add Missing Type Hints" in result.output
    assert "File: test.py" in result.output
    assert "IMPORTANT CONSTRAINTS" in result.output
