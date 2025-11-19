from __future__ import annotations

from pathlib import Path
from typing import Optional

import click

from codesage.config.loader import load_config
from codesage.config.org import OrgConfig
from codesage.org.aggregator import OrgAggregator
from codesage.org.report_generator import (
    render_org_report_json,
    render_org_report_markdown,
)


from codesage.audit.models import AuditEvent
from datetime import datetime

@click.command("org-report", help="Generate an organization-level governance report from multiple project artifacts.")
@click.option(
    "--config",
    "config_path_str",
    default=".codesage.yaml",
    help="Path to the codesage configuration file.",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--out-json",
    "out_json_path_str",
    default=None,
    help="Path to save the JSON organization report.",
    type=click.Path(writable=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--out-md",
    "out_md_path_str",
    default=None,
    help="Path to save the Markdown organization report.",
    type=click.Path(writable=True, dir_okay=False, path_type=Path),
)
@click.pass_context
def org_report(
    ctx,
    config_path_str: Path,
    out_json_path_str: Optional[Path],
    out_md_path_str: Optional[Path],
) -> None:
    """
    Generates an organization-level report by aggregating data from multiple
    pre-existing project snapshots, reports, and governance plans.
    """
    audit_logger = ctx.obj.audit_logger
    try:
        if not out_json_path_str and not out_md_path_str:
            raise click.UsageError("At least one output format (--out-json or --out-md) must be specified.")

        click.echo(f"Loading organization configuration from: {config_path_str}")
        config = load_config(config_path_str.parent)
        org_config = OrgConfig.model_validate(config.get("org", {}))

        if not org_config.projects:
            raise click.ClickException("No projects found in the 'org' configuration section. Nothing to do.")

        click.echo(f"Found {len(org_config.projects)} projects. Starting aggregation...")
        aggregator = OrgAggregator(org_config)
        overview = aggregator.aggregate()
        click.echo("Aggregation complete.")

        if out_json_path_str:
            click.echo(f"Writing JSON report to: {out_json_path_str}")
            json_report = render_org_report_json(overview)
            out_json_path_str.write_text(json_report, encoding="utf-8")

        if out_md_path_str:
            click.echo(f"Writing Markdown report to: {out_md_path_str}")
            md_report = render_org_report_markdown(overview)
            out_md_path_str.write_text(md_report, encoding="utf-8")

        click.echo("Organization report generation finished successfully.")
    finally:
        audit_logger.log(
            AuditEvent(
                timestamp=datetime.now(),
                event_type="cli.org_report",
                project_name=None,
                command="org-report",
                args={
                    "config_path_str": str(config_path_str),
                    "out_json_path_str": str(out_json_path_str) if out_json_path_str else None,
                    "out_md_path_str": str(out_md_path_str) if out_md_path_str else None,
                },
            )
        )
