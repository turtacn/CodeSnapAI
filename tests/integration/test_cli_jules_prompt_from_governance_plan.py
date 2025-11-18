import pytest
from click.testing import CliRunner
from codesage.cli.main import main
import yaml

@pytest.fixture
def governance_plan_file(tmp_path):
    """Creates a dummy governance_plan.yaml file."""
    plan_content = {
        "project_name": "test-project",
        "project_version": "1.0.0",
        "created_at": "2024-01-01T00:00:00",
        "summary": {"total_tasks": 1},
        "groups": [
            {
                "id": "group1",
                "name": "High Complexity Functions",
                "group_by": "rule_id",
                "tasks": [
                    {
                        "id": "test.py:PY_HIGH_CYCLOMATIC_FUNCTION:1",
                        "rule_id": "PY_HIGH_CYCLOMATIC_FUNCTION",
                        "language": "python",
                        "description": "High complexity",
                        "file_path": "test.py",
                        "priority": 1,
                        "risk_level": "low",
                        "status": "pending",
                        "metadata": {"start_line": 1, "end_line": 10},
                    }
                ]
            }
        ]
    }
    plan_file = tmp_path / "governance_plan.yaml"
    with open(plan_file, "w") as f:
        yaml.dump(plan_content, f)
    return str(plan_file)

def test_cli_jules_prompt_from_governance_plan(governance_plan_file):
    """
    Tests the `codesage jules-prompt` command with a governance plan.
    """
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "jules-prompt",
            "--plan",
            governance_plan_file,
            "--task-id",
            "test.py:PY_HIGH_CYCLOMATIC_FUNCTION:1",
        ],
    )

    assert result.exit_code == 0
    assert "TASK: Refactor High-Complexity Function" in result.output
    assert "File: test.py" in result.output
    assert "IMPORTANT CONSTRAINTS" in result.output
