import click
import yaml
from pathlib import Path

from codesage.config.governance import GovernanceConfig
from codesage.governance.task_builder import TaskBuilder
from codesage.snapshot.models import ProjectSnapshot
from codesage.utils.file_utils import read_yaml_file, write_yaml_file

from codesage.audit.models import AuditEvent
from datetime import datetime

from codesage.snapshot.versioning import SnapshotVersionManager
from codesage.config.defaults import SNAPSHOT_DIR, DEFAULT_SNAPSHOT_CONFIG

@click.command(name="governance-plan", help="Generate a governance plan from a project snapshot.")
@click.option(
    "--snapshot-version",
    "snapshot_version",
    required=True,
    help="The version of the snapshot to use.",
)
@click.option(
    "--project",
    "project_name",
    required=True,
    help="The name of the project.",
)
@click.option(
    "--output",
    "output_path",
    required=True,
    type=click.Path(dir_okay=False, resolve_path=True),
    help="Path to the output governance plan YAML file.",
)
@click.option("--group-by", type=click.Choice(["rule", "file", "risk_level"]), help="Override the grouping strategy.")
@click.option("--max-tasks-per-file", type=int, help="Override the max tasks per file limit.")
@click.pass_context
def governance_plan(
    ctx,
    snapshot_version: str,
    project_name: str,
    output_path: str,
    group_by: str | None,
    max_tasks_per_file: int | None,
):
    """
    Generates a governance plan from a project snapshot.
    """
    audit_logger = ctx.obj.audit_logger
    try:
        manager = SnapshotVersionManager(SNAPSHOT_DIR, project_name, DEFAULT_SNAPSHOT_CONFIG['snapshot'])
        snapshot = manager.load_snapshot(snapshot_version)
        if not snapshot:
            click.echo(f"Snapshot {snapshot_version} not found for project '{project_name}'.", err=True)
            return

        # Apply config overrides
        config = GovernanceConfig.default()
        if group_by:
            config.group_by = group_by
        if max_tasks_per_file:
            config.max_tasks_per_file = max_tasks_per_file

        click.echo("Building governance plan...")
        builder = TaskBuilder(config)
        plan = builder.build_plan(snapshot)

        # Serialize plan to YAML
        plan_dict = plan.model_dump(mode="json")

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        write_yaml_file(plan_dict, output_file)

        click.echo(f"Governance plan successfully saved to {output_path}")
        click.echo(f"Summary: {plan.summary['total_tasks']} tasks found.")
    finally:
        audit_logger.log(
            AuditEvent(
                timestamp=datetime.now(),
                event_type="cli.governance_plan",
                project_name=project_name,
                command="governance-plan",
                args={
                    "snapshot_version": snapshot_version,
                    "output_path": output_path,
                    "group_by": group_by,
                    "max_tasks_per_file": max_tasks_per_file,
                },
            )
        )

def register(cli: click.Group) -> None:
    """Registers the governance-plan command with the main CLI group."""
    cli.add_command(governance_plan)
