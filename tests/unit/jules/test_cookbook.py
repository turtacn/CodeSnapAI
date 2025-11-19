import pytest
from codesage.governance.task_models import GovernanceTask
from codesage.jules.cookbook import get_recipe_for_task

@pytest.fixture
def sample_task() -> GovernanceTask:
    """Provides a sample GovernanceTask for testing."""
    return GovernanceTask(
        id="test_task",
        project_name="test_project",
        rule_id="PY_HIGH_CYCLOMATIC_FUNCTION",
        language="python",
        description="High complexity",
        file_path="test.py",
        priority=1,
        risk_level="low",
        status="pending",
        metadata={"start_line": 1, "end_line": 10},
    )

def test_cookbook_recipe_for_high_complexity(sample_task: GovernanceTask):
    """
    Tests that the correct recipe is selected for a high-complexity Python function.
    """
    recipe = get_recipe_for_task(sample_task)
    assert recipe is not None
    assert recipe.id == "python_high_complexity"
    assert recipe.template_id == "high_complexity_refactor"

def test_cookbook_recipe_for_shell_script_hardening(sample_task: GovernanceTask):
    """
    Tests that the correct recipe is selected for shell script hardening.
    """
    sample_task.language = "shell"
    sample_task.rule_id = "SH_INSECURE_SCRIPT"
    recipe = get_recipe_for_task(sample_task)
    assert recipe is not None
    assert recipe.id == "shell_hardening"
    assert recipe.template_id == "shell_script_hardening"

def test_cookbook_fallback_recipe(sample_task: GovernanceTask):
    """
    Tests that a fallback recipe is used when a specific rule is not found.
    """
    sample_task.rule_id = "SOME_OTHER_PYTHON_RULE"
    recipe = get_recipe_for_task(sample_task)
    assert recipe is not None
    assert recipe.id == "python_default"
    assert recipe.template_id == "python_default"

def test_cookbook_no_recipe_for_unknown_language(sample_task: GovernanceTask):
    """
    Tests that no recipe is returned for an unsupported language.
    """
    sample_task.language = "unknown_language"
    recipe = get_recipe_for_task(sample_task)
    assert recipe is None
