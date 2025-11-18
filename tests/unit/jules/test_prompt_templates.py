import pytest
from codesage.jules.prompt_templates import get_template_for_rule, JulesPromptTemplate

def test_template_selection_by_rule_and_language():
    """
    Tests that the correct template is selected based on rule ID and language.
    """
    # Test Python high complexity
    template = get_template_for_rule("PY_HIGH_CYCLOMATIC_FUNCTION", "python")
    assert template is not None
    assert template.id == "high_complexity_refactor"

    # Test Python type hints
    template = get_template_for_rule("PY_MISSING_TYPE_HINTS", "python")
    assert template is not None
    assert template.id == "add_type_hints_public_api"

    # Test Shell script hardening
    template = get_template_for_rule("SH_INSECURE_SCRIPT", "shell")
    assert template is not None
    assert template.id == "shell_script_hardening"

    # Test Go default
    template = get_template_for_rule("SOME_GO_RULE", "go")
    assert template is not None
    assert template.id == "go_refactor_basic"

    # Test fallback to Python default
    template = get_template_for_rule("SOME_OTHER_PYTHON_RULE", "python")
    assert template is not None
    assert template.id == "python_default"

    # Test unknown language
    template = get_template_for_rule("SOME_RULE", "unknown_language")
    assert template is None
