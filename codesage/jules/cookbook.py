from typing import List, Optional
from pydantic import BaseModel
from codesage.governance.task_models import GovernanceTask

# --- Jules Recipes ---

class JulesRecipe(BaseModel):
    """
    A recipe defines a strategy for generating a Jules prompt for a specific scenario.
    """
    id: str
    name: str
    supported_rules: List[str]
    language: str
    template_id: str

# A predefined list of recipes that map rules and languages to prompt templates.
RECIPES: List[JulesRecipe] = [
    JulesRecipe(
        id="python_high_complexity",
        name="Refactor High-Complexity Python Function",
        supported_rules=["PY_HIGH_CYCLOMATIC_FUNCTION"],
        language="python",
        template_id="high_complexity_refactor",
    ),
    JulesRecipe(
        id="python_add_type_hints",
        name="Add Type Hints to Python Public API",
        supported_rules=["PY_MISSING_TYPE_HINTS"],
        language="python",
        template_id="add_type_hints_public_api",
    ),
    JulesRecipe(
        id="shell_hardening",
        name="Harden Shell Script",
        supported_rules=["SH_INSECURE_SCRIPT"],
        language="shell",
        template_id="shell_script_hardening",
    ),
    # --- Default/Fallback Recipes ---
    JulesRecipe(
        id="python_default",
        name="Default Python Refactoring",
        supported_rules=[],  # An empty list indicates this is a fallback
        language="python",
        template_id="python_default",
    ),
    JulesRecipe(
        id="go_default",
        name="Default Go Refactoring",
        supported_rules=[],
        language="go",
        template_id="go_refactor_basic",
    ),
]

def get_recipe_for_task(task: GovernanceTask) -> Optional[JulesRecipe]:
    """
    Selects the appropriate recipe for a given governance task.

    It first tries to find a recipe that explicitly supports the rule_id for the task's language.
    If no specific recipe is found, it falls back to a default recipe for that language.
    """
    # First, try to find a specific recipe for the rule and language.
    for recipe in RECIPES:
        if task.language == recipe.language and task.rule_id in recipe.supported_rules:
            return recipe

    # If no specific recipe is found, fall back to the default for the language.
    for recipe in RECIPES:
        if task.language == recipe.language and not recipe.supported_rules:
            return recipe

    return None
