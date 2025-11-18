from codesage.config.jules import JulesPromptConfig
from codesage.governance.jules_bridge import JulesTaskView
from codesage.jules.prompt_templates import JulesPromptTemplate


def build_prompt(
    view: JulesTaskView,
    template: JulesPromptTemplate,
    config: JulesPromptConfig,
) -> str:
    """
    Builds the final prompt string from a JulesTaskView, a template, and configuration.
    """
    # Truncate the code snippet if it exceeds the max number of lines
    code_lines = view.code_snippet.split('\n')
    if len(code_lines) > config.max_code_context_lines:
        code_snippet = '\n'.join(code_lines[:config.max_code_context_lines])
        code_snippet += "\n... (code truncated)"
    else:
        code_snippet = view.code_snippet

    llm_hint = view.llm_hint or ""
    if not config.include_llm_hint:
        llm_hint = ""

    body = template.body_format.format(
        file_path=view.file_path,
        line=view.line or "",
        language=view.language,
        function_name=view.function_name or "",
        issue_message=view.issue_message,
        goal_description=view.goal_description,
        code_snippet=code_snippet,
        llm_hint=llm_hint,
    )

    # Combine header, body, and footer to form the final prompt
    prompt = "\n\n".join([template.header, body.strip(), template.footer])
    return prompt
