from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from codesage.config.llm import LLMConfig
    from codesage.snapshot.models import FileSnapshot, Issue, IssueLocation, ProjectSnapshot


def extract_code_context(file: "FileSnapshot", location: "IssueLocation", max_lines: int) -> str:
    try:
        with open(file.path, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return ""

    start_line = max(0, location.line - (max_lines // 2))
    end_line = min(len(lines), location.line + (max_lines // 2))

    return "".join(lines[start_line:end_line])


def build_issue_prompt(
    issue: "Issue",
    file: "FileSnapshot",
    project: "ProjectSnapshot",
    config: "LLMConfig",
) -> str:
    code_snippet = extract_code_context(file, issue.location, config.max_code_context_lines)

    prompt = f"""
        Analyze the following code quality issue and provide a brief, actionable suggestion for remediation.

        **Project:** {project.metadata.project_name}
        **File:** {file.path}
        **Line:** {issue.location.line}
        **Rule ID:** {issue.rule_id}
        **Severity:** {issue.severity}
        **Message:** {issue.message}

        **Code Snippet:**
        ```
        {code_snippet}
        ```

        **Suggestion:**
    """

    return prompt
