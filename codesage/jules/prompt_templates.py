from typing import Dict, List, Optional
from pydantic import BaseModel

# --- Guardrails and Standard Instructions ---

HEADER = """
You are an expert software engineer specializing in local code refactoring.
Your task is to analyze a specific code snippet, identify the issue described, and provide a patch to fix it.
You must follow all instructions and constraints meticulously.
"""

FOOTER = """
### IMPORTANT CONSTRAINTS:
1.  **Local Changes Only**: Your proposed changes MUST be confined to the provided code snippet and its immediate context within the file. Do not suggest changes to other files, project structure, or dependencies.
2.  **No Architectural Decisions**: Do not make architectural or design decisions. Your focus is on improving the existing code's quality, not redesigning it.
3.  **No Dependency Changes**: Do not add, remove, or change any project dependencies or build configurations (e.g., `pyproject.toml`, `go.mod`, `package.json`).
4.  **Format**: Provide your response as a single Git-style diff block. Do not include any other text before or after the diff.
5.  **Explanation**: After the diff, provide a brief, clear explanation of your changes.
"""

# --- Prompt Templates ---

class JulesPromptTemplate(BaseModel):
    """A structured template for generating prompts for Jules."""
    id: str
    description: str
    header: str
    body_format: str
    footer: str

TEMPLATES: Dict[str, JulesPromptTemplate] = {
    "high_complexity_refactor": JulesPromptTemplate(
        id="high_complexity_refactor",
        description="For refactoring functions with high cyclomatic complexity.",
        header=HEADER,
        body_format="""
### TASK: Refactor High-Complexity Function

File: {file_path}
Line: {line}
Function: {function_name}
Language: {language}
Issue: {issue_message}

Goal: {goal_description}
LLM Hint: {llm_hint}

Code Snippet:
```
{code_snippet}
```
""",
        footer=FOOTER,
    ),
    "add_type_hints_public_api": JulesPromptTemplate(
        id="add_type_hints_public_api",
        description="For adding missing type hints to public APIs.",
        header=HEADER,
        body_format="""
### TASK: Add Missing Type Hints

File: {file_path}
Line: {line}
Function: {function_name}
Language: {language}
Issue: {issue_message}

Goal: {goal_description}
LLM Hint: {llm_hint}

Code Snippet:
```
{code_snippet}
```
""",
        footer=FOOTER,
    ),
    "shell_script_hardening": JulesPromptTemplate(
        id="shell_script_hardening",
        description="To improve the security and robustness of shell scripts.",
        header=HEADER,
        body_format="""
### TASK: Harden Shell Script

File: {file_path}
Line: {line}
Language: {language}
Issue: {issue_message}

Goal: {goal_description}
LLM Hint: {llm_hint}

Code Snippet:
```
{code_snippet}
```
""",
        footer=FOOTER,
    ),
    "go_refactor_basic": JulesPromptTemplate(
        id="go_refactor_basic",
        description="For basic refactoring of Go code.",
        header=HEADER,
        body_format="""
### TASK: Basic Go Refactoring

File: {file_path}
Line: {line}
Function: {function_name}
Language: {language}
Issue: {issue_message}

Goal: {goal_description}
LLM Hint: {llm_hint}

Code Snippet:
```
{code_snippet}
```
""",
        footer=FOOTER,
    ),
    "python_default": JulesPromptTemplate(
        id="python_default",
        description="Default template for Python-related issues.",
        header=HEADER,
        body_format="""
### TASK: Fix Python Code Quality Issue

File: {file_path}
Line: {line}
Function: {function_name}
Language: {language}
Issue: {issue_message}

Goal: {goal_description}
LLM Hint: {llm_hint}

Code Snippet:
```
{code_snippet}
```
""",
        footer=FOOTER,
    ),
}

# --- Template Selection Logic ---

RULE_TO_TEMPLATE_MAP: Dict[str, Dict[str, str]] = {
    "python": {
        "PY_HIGH_CYCLOMATIC_FUNCTION": "high_complexity_refactor",
        "PY_MISSING_TYPE_HINTS": "add_type_hints_public_api",
    },
    "shell": {
        "SH_INSECURE_SCRIPT": "shell_script_hardening",
    },
    "go": {},
}

LANGUAGE_DEFAULT_TEMPLATE_MAP: Dict[str, str] = {
    "python": "python_default",
    "go": "go_refactor_basic",
    "shell": "shell_script_hardening",
}

def get_template_for_rule(rule_id: str, language: str) -> Optional[JulesPromptTemplate]:
    """
    Selects the appropriate prompt template based on the rule ID and language.
    """
    language_map = RULE_TO_TEMPLATE_MAP.get(language, {})
    template_id = language_map.get(rule_id)

    if not template_id:
        template_id = LANGUAGE_DEFAULT_TEMPLATE_MAP.get(language)

    return TEMPLATES.get(template_id) if template_id else None
