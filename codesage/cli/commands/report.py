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


@click.command('report', help='Generate reports from a project snapshot.')
@click.option('--input', 'input_path', required=True, type=click.Path(exists=True), help='Path to the snapshot YAML file.')
@click.option('--out-json', 'out_json_path', type=click.Path(), help='Path to save the JSON report.')
@click.option('--out-md', 'out_md_path', type=click.Path(), help='Path to save the Markdown report.')
@click.option('--out-junit', 'out_junit_path', type=click.Path(), help='Path to save the JUnit XML report.')
@click.option('--ci-policy-strict', 'ci_policy_strict', is_flag=True, help='Enable strict CI policy.')
def report(input_path: str, out_json_path: Optional[str], out_md_path: Optional[str], out_junit_path: Optional[str], ci_policy_strict: bool):
    with open(input_path, 'r') as f:
        snapshot_data = yaml.safe_load(f)

    snapshot = ProjectSnapshot(**snapshot_data)

    project_summary, file_summaries = ReportGenerator.from_snapshot(snapshot)

    if out_json_path:
        json_report = render_json(project_summary, file_summaries)
        with open(out_json_path, 'w') as f:
            f.write(json_report)
        click.echo(f"JSON report saved to {out_json_path}")

    if out_md_path:
        md_report = render_markdown(project_summary, file_summaries)
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
        should_fail, reasons = evaluate_ci_policy(project_summary, ci_policy)
        if should_fail:
            click.echo("CI policy failed:", err=True)
            for reason in reasons:
                click.echo(f"- {reason}", err=True)
            raise click.exceptions.Exit(1)
        else:
            click.echo("CI policy passed.")
