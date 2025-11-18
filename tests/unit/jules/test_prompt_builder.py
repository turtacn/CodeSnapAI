import pytest
from codesage.config.jules import JulesPromptConfig
from codesage.governance.jules_bridge import JulesTaskView
from codesage.jules.prompt_templates import TEMPLATES
from codesage.jules.prompt_builder import build_prompt

@pytest.fixture
def sample_task_view() -> JulesTaskView:
    """Provides a sample JulesTaskView for testing."""
    return JulesTaskView(
        file_path="src/main.py",
        language="python",
        code_snippet="def my_func(a, b):\n    return a + b",
        issue_message="Function is too complex.",
        goal_description="Refactor the function to reduce complexity.",
        line=10,
        function_name="my_func",
        llm_hint="Consider using a different algorithm.",
        notes_for_human_reviewer="This is a test note."
    )

def test_prompt_contains_mandatory_sections(sample_task_view: JulesTaskView):
    """
    Tests that the generated prompt contains all the mandatory sections.
    """
    template = TEMPLATES["high_complexity_refactor"]
    config = JulesPromptConfig.default()
    prompt = build_prompt(sample_task_view, template, config)

    assert "TASK: Refactor High-Complexity Function" in prompt
    assert "File: src/main.py" in prompt
    assert "Line: 10" in prompt
    assert "Function: my_func" in prompt
    assert "def my_func(a, b):" in prompt
    assert "IMPORTANT CONSTRAINTS" in prompt

def test_prompt_respects_max_code_context_lines(sample_task_view: JulesTaskView):
    """
    Tests that the code snippet in the prompt is truncated if it's too long.
    """
    template = TEMPLATES["high_complexity_refactor"]
    config = JulesPromptConfig(max_code_context_lines=1)

    sample_task_view.code_snippet = "line1\nline2\nline3"

    prompt = build_prompt(sample_task_view, template, config)

    assert "line1" in prompt
    assert "line2" not in prompt
    assert "... (code truncated)" in prompt

def test_prompt_llm_hint_inclusion(sample_task_view: JulesTaskView):
    """
    Tests that the llm_hint is included or excluded based on the config.
    """
    template = TEMPLATES["high_complexity_refactor"]

    # Test inclusion
    config = JulesPromptConfig(include_llm_hint=True)
    prompt = build_prompt(sample_task_view, template, config)
    # The default template body does not include llm_hint, so we can't assert its presence.
    # We will modify the template to include it for the test.
    template.body_format += "\nLLM Hint: {llm_hint}"
    prompt = build_prompt(sample_task_view, template, config)
    assert "LLM Hint: Consider using a different algorithm." in prompt

    # Test exclusion
    config = JulesPromptConfig(include_llm_hint=False)
    prompt = build_prompt(sample_task_view, template, config)
    assert "LLM Hint: Consider using a different algorithm." not in prompt
