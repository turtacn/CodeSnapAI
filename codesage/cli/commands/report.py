from __future__ import annotations
import click
import yaml
from typing import Optional
from codesage.snapshot.models import ProjectSnapshot
from codesage.report.generator import ReportGenerator
from codesage.report.format_json import render_json
from codesage.report.format_markdown import render_markdown
from codesage.report.format_junit import render_junit_xml
from codesage.config.ci import CIPolicyConfig
from codesage.ci.policy import evaluate_ci_policy


from codesage.audit.models import AuditEvent
from datetime import datetime

import os
from codesage.snapshot.versioning import SnapshotVersionManager

# This would be loaded from the config file
# For now, we'll use a default config.
DEFAULT_CONFIG = {
    "snapshot": {
        "versioning": {
            "max_versions": 10,
            "retention_days": 30
        }
    }
}
SNAPSHOT_DIR = ".codesage/snapshots"

def find_project_root(path):
    current = os.path.abspath(path)
    while True:
        if ".codesage" in os.listdir(current):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent

@click.command('report', help='Generate reports from a project snapshot.')
@click.option('--input', 'input_path', required=True, type=click.Path(exists=True), help='Path to the snapshot YAML file or project directory.')
@click.option('--out-json', 'out_json_path', type=click.Path(), help='Path to save the JSON report.')
@click.option('--out-md', 'out_md_path', type=click.Path(), help='Path to save the Markdown report.')
@click.option('--out-junit', 'out_junit_path', type=click.Path(), help='Path to save the JUnit XML report.')
@click.option('--ci-policy-strict', 'ci_policy_strict', is_flag=True, help='Enable strict CI policy.')
@click.pass_context
def report(ctx, input_path: str, out_json_path: Optional[str], out_md_path: Optional[str], out_junit_path: Optional[str], ci_policy_strict: bool):
    audit_logger = ctx.obj.audit_logger
    project_name = None
    try:
        if os.path.isdir(input_path):
            project_root = find_project_root(input_path)
            if not project_root:
                click.echo("Could not find a .codesage directory in the project.", err=True)
                return
            snapshot_dir = os.path.join(project_root, SNAPSHOT_DIR)
            manager = SnapshotVersionManager(snapshot_dir, DEFAULT_CONFIG['snapshot'])
            snapshots = manager.list_snapshots()
            if not snapshots:
                click.echo("No snapshots found for this project. Please create a snapshot first using 'codesage snapshot create'.", err=True)
                return
            latest_snapshot = sorted(snapshots, key=lambda s: s['timestamp'], reverse=True)[0]
            snapshot_file = latest_snapshot['path']
        else:
            snapshot_file = input_path

        with open(snapshot_file, 'r') as f:
            snapshot_data = yaml.safe_load(f)

        snapshot = ProjectSnapshot.model_validate(snapshot_data)
        project_name = snapshot.metadata.project_name

        project_summary, file_summaries = ReportGenerator.from_snapshot(snapshot)

        # Policy evaluation
        from codesage.config.loader import load_config
        from codesage.config.policy import PolicyConfig
        from codesage.policy.parser import load_policy
        from codesage.policy.engine import evaluate_project_policies
        from pathlib import Path

        raw_config = load_config()
        policy_config = PolicyConfig(**raw_config.get('policy', {}))
        policy_decisions = []
        if policy_config.project_policy_path:
            policy_path = Path(policy_config.project_policy_path)
            if policy_path.exists():
                try:
                    policy = load_policy(policy_path)
                    policy_decisions = evaluate_project_policies(policy, snapshot, project_summary, None, None)
                except Exception as e:
                    click.echo(f"Error loading or evaluating policy: {e}", err=True)
                    raise click.exceptions.Exit(1)

        if out_json_path:
            json_report = render_json(project_summary, file_summaries)
            with open(out_json_path, 'w') as f:
                f.write(json_report)
            click.echo(f"JSON report saved to {out_json_path}")

        if out_md_path:
            md_report = render_markdown(project_summary, file_summaries) # TODO: Update render_markdown to accept Report object
            with open(out_md_path, 'w') as f:
                f.write(md_report)
            click.echo(f"Markdown report saved to {out_md_path}")

        if out_junit_path:
            junit_report = render_junit_xml(snapshot)
            with open(out_junit_path, 'w') as f:
                f.write(junit_report)
            click.echo(f"JUnit XML report saved to {out_junit_path}")

        if ci_policy_strict:
            ci_policy = CIPolicyConfig(
                enabled=True,
                fail_on_error_issues=True,
                max_error_issues=0,
                max_high_risk_files=0
            )
            should_fail, reasons = evaluate_ci_policy(project_summary, ci_policy, policy_decisions=policy_decisions)
            if should_fail:
                click.echo("CI policy failed:", err=True)
                for reason in reasons:
                    click.echo(f"- {reason}", err=True)
                raise click.exceptions.Exit(1)
            else:
                click.echo("CI policy passed.")
    finally:
        audit_logger.log(
            AuditEvent(
                timestamp=datetime.now(),
                event_type="cli.report",
                project_name=project_name,
                command="report",
                args={
                    "input_path": input_path,
                    "out_json_path": out_json_path,
                    "out_md_path": out_md_path,
                    "out_junit_path": out_junit_path,
                    "ci_policy_strict": ci_policy_strict,
                },
            )
        )
