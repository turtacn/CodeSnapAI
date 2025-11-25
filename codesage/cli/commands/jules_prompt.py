import click
import yaml
from typing import Optional, Dict, Any

from codesage.config.jules import JulesPromptConfig
from codesage.governance.task_models import GovernancePlan, GovernanceTask
from codesage.governance.jules_bridge import JulesTaskView
from codesage.jules.cookbook import get_recipe_for_task
from codesage.jules.prompt_templates import TEMPLATES
from codesage.jules.prompt_builder import build_prompt
from codesage.utils.file_utils import read_yaml_file

from codesage.audit.models import AuditEvent
from datetime import datetime

@click.command('jules-prompt', help="Generate a Jules prompt for a specific governance task.")
@click.option('--plan', 'plan_path', type=click.Path(exists=True), help="Path to the governance_plan.yaml file.")
@click.option('--task-id', help="The ID of the task within the governance plan.")
@click.option('--task', 'task_path', type=click.Path(exists=True), help="Path to a single GovernanceTask YAML/JSON file.")
@click.pass_context
def jules_prompt(ctx, plan_path: Optional[str], task_id: Optional[str], task_path: Optional[str]):
    """
    Generates a prompt for Jules from a governance task.
    """
    audit_logger = ctx.obj.audit_logger
    project_name = None
    try:
        if task_path:
            task_data = read_yaml_file(task_path)
            task = GovernanceTask(**task_data)
            project_name = task.project_name
        elif plan_path and task_id:
            plan_data = read_yaml_file(plan_path)
            plan = GovernancePlan(**plan_data)
            project_name = plan.project_name
            task = None
            for group in plan.groups:
                task = next((t for t in group.tasks if t.id == task_id), None)
                if task:
                    break
            if not task:
                click.echo(f"Error: Task with ID '{task_id}' not found in the plan.", err=True)
                return
        else:
            click.echo("Error: You must provide either --task <path> or both --plan <path> and --task-id <id>.", err=True)
            return

        # For now, we'll create a default JulesPromptConfig.
        # In a real application, this would come from the loaded codesage config.
        config = JulesPromptConfig.default()

        # Get the recipe and template
        recipe = get_recipe_for_task(task)
        if not recipe:
            click.echo(f"Error: No recipe found for task language '{task.language}' and rule '{task.rule_id}'.", err=True)
            return

        template = TEMPLATES.get(recipe.template_id)
        if not template:
            click.echo(f"Error: Template with ID '{recipe.template_id}' not found.", err=True)
            return

        # The JulesTaskView requires a code snippet, which we don't have in the GovernanceTask alone.
        # For this CLI tool, we'll use a placeholder. A more advanced implementation
        # would need access to the project snapshot to get the real code.
        # We will use the `llm_hint` field from the task metadata if it exists.

        code_snippet_placeholder = task.metadata.get("code_snippet", "[Code snippet not available in this context. Please refer to the file and line number.]")

        # Create a simple JulesTaskView from the task
        view = JulesTaskView(
            file_path=task.file_path,
            language=task.language,
            code_snippet=code_snippet_placeholder,
            issue_message=task.description,
            goal_description=task.metadata.get("goal_description", "Fix the issue described above."),
            line=task.metadata.get("start_line"),
            function_name=task.metadata.get("symbol"),
            llm_hint=task.llm_hint,
            notes_for_human_reviewer="This is a test note."
        )

        # Build and print the prompt
        prompt = build_prompt(view, template, config)
        click.echo(prompt)
    finally:
        audit_logger.log(
            AuditEvent(
                timestamp=datetime.now(),
                event_type="cli.jules_prompt",
                project_name=project_name,
                command="jules-prompt",
                args={
                    "plan_path": plan_path,
                    "task_id": task_id,
                    "task_path": task_path,
                },
            )
        )
