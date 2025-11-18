from __future__ import annotations
import os
from pydantic import BaseModel
from typing import Optional, List, Tuple

from codesage.config.jules import JulesPromptConfig
from codesage.governance.task_models import GovernanceTask
from codesage.snapshot.models import ProjectSnapshot
from codesage.jules.prompt_templates import JulesPromptTemplate, get_template_for_rule


class JulesTaskView(BaseModel):
    file_path: str
    language: str
    line: Optional[int]
    function_name: Optional[str]
    issue_message: str
    goal_description: str
    code_snippet: str
    llm_hint: Optional[str]
    notes_for_human_reviewer: str


def _extract_code_context(
    file_path: str, line: Optional[int], max_lines: int
) -> str:
    """Extracts a snippet of code centered around a specific line."""
    if not line or not os.path.exists(file_path):
        return ""

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        start = max(0, line - 1 - max_lines // 2)
        end = min(len(lines), line + max_lines // 2)

        return "".join(lines[start:end])
    except Exception:
        return f"Could not read code snippet from {file_path}"


def build_jules_task_view(
    task: GovernanceTask,
    snapshot: ProjectSnapshot,
    max_context_lines: int,
) -> JulesTaskView:
    line = task.metadata.get("line")
    code_snippet = _extract_code_context(
        task.file_path, line, max_context_lines
    )

    goal_description = (
        f"Refactor or fix the code in `{task.file_path}` near line {line} "
        f"to address the issue: '{task.metadata.get('severity')}: {task.rule_id}'. "
        "Your goal is to provide a specific code patch to resolve this. "
        "Do not run tests, modify CI/CD configurations, or change unrelated files."
    )

    notes_for_human = (
        "The suggested changes from the AI assistant must be carefully reviewed and "
        "applied by a human developer. This assistant cannot directly modify the repository "
        "or deployment pipelines and its suggestions are not a substitute for expert review."
    )

    view = JulesTaskView(
        file_path=task.file_path,
        language=task.language,
        line=line,
        function_name=task.metadata.get("symbol"),
        issue_message=task.description,
        goal_description=goal_description,
        code_snippet=code_snippet,
        llm_hint=task.llm_hint,
        notes_for_human_reviewer=notes_for_human,
    )
    return view


def build_view_and_template_for_task(
    task: GovernanceTask,
    snapshot: ProjectSnapshot,
    jules_config: JulesPromptConfig
) -> Tuple[JulesTaskView, Optional[JulesPromptTemplate]]:
    """
    A one-stop function to get the JulesTaskView and the appropriate prompt template.
    """
    # Build the JulesTaskView
    view = build_jules_task_view(
        task=task,
        snapshot=snapshot,
        max_context_lines=jules_config.max_code_context_lines,
    )

    # Select the template
    template = get_template_for_rule(task.rule_id, task.language)

    return view, template
