import click
import os
import sys
from pathlib import Path
from typing import Optional

from codesage.semantic_digest.python_snapshot_builder import PythonSemanticSnapshotBuilder, SnapshotConfig
from codesage.semantic_digest.go_snapshot_builder import GoSemanticSnapshotBuilder
from codesage.semantic_digest.shell_snapshot_builder import ShellSemanticSnapshotBuilder
from codesage.snapshot.models import ProjectSnapshot, Issue, IssueLocation
from codesage.reporters import ConsoleReporter, JsonReporter, GitHubPRReporter
from codesage.cli.plugin_loader import PluginManager
from codesage.history.store import StorageEngine
from codesage.core.interfaces import CodeIssue

def get_builder(language: str, path: Path):
    config = SnapshotConfig()
    if language == 'python':
        return PythonSemanticSnapshotBuilder(path, config)
    elif language == 'go':
        return GoSemanticSnapshotBuilder(path, config)
    elif language == 'shell':
        return ShellSemanticSnapshotBuilder(path, config)
    else:
        return None

@click.command('scan')
@click.argument('path', type=click.Path(exists=True, dir_okay=True))
@click.option('--language', '-l', type=click.Choice(['python', 'go', 'shell']), default='python', help='Language to analyze.')
@click.option('--reporter', '-r', type=click.Choice(['console', 'json', 'github']), default='console', help='Reporter to use.')
@click.option('--output', '-o', help='Output path for JSON reporter.')
@click.option('--fail-on-high', is_flag=True, help='Exit with non-zero code if high severity issues are found.')
@click.option('--ci-mode', is_flag=True, help='Enable CI mode (auto-detect GitHub environment).')
@click.option('--plugins-dir', default='.codesage/plugins', help='Directory containing plugins.')
@click.option('--db-url', default='sqlite:///codesage.db', help='Database URL for storage.')
@click.pass_context
def scan(ctx, path, language, reporter, output, fail_on_high, ci_mode, plugins_dir, db_url):
    """
    Scan the codebase and report issues.
    """
    # 1. Initialize Database
    try:
        storage = StorageEngine(db_url)
        click.echo(f"Connected to storage: {db_url}")
    except Exception as e:
        click.echo(f"Warning: Could not connect to storage: {e}", err=True)
        storage = None

    # 2. Load Plugins
    plugin_manager = PluginManager(plugins_dir)
    plugin_manager.load_plugins()

    click.echo(f"Scanning {path} for {language}...")

    root_path = Path(path)
    builder = get_builder(language, root_path)

    if not builder:
        click.echo(f"Unsupported language: {language}", err=True)
        ctx.exit(1)

    try:
        snapshot: ProjectSnapshot = builder.build()

        # 3. Apply Custom Rules (Plugins)
        for rule in plugin_manager.rules:
            for file_path, file_snapshot in snapshot.files.items():
                try:
                    content = ""
                    full_path = root_path / file_path
                    if full_path.exists():
                        content = full_path.read_text(errors='ignore')

                    issues = rule.check(str(file_path), content, {})
                    if issues:
                        for i in issues:
                            # Convert plugin CodeIssue to standard Issue model

                            # Map severity to Issue severity Literal
                            severity = "warning"
                            if i.severity.lower() in ["info", "warning", "error"]:
                                severity = i.severity.lower()
                            elif i.severity.lower() == "high":
                                severity = "error"
                            elif i.severity.lower() == "low":
                                severity = "info"

                            new_issue = Issue(
                                rule_id=rule.id,
                                severity=severity,
                                message=i.description,
                                location=IssueLocation(
                                    file_path=str(file_path),
                                    line=i.line_number
                                ),
                                symbol=None,
                                tags=["custom-rule"]
                            )

                            if file_snapshot.issues is None:
                                file_snapshot.issues = []
                            file_snapshot.issues.append(new_issue)

                except Exception as e:
                     click.echo(f"Error running rule {rule.id} on {file_path}: {e}", err=True)

        # 4. Save to Storage
        if storage:
            try:
                storage.save_snapshot(snapshot.metadata.project_name, snapshot)
                click.echo("Snapshot saved to database.")
            except Exception as e:
                 click.echo(f"Failed to save snapshot: {e}", err=True)

    except Exception as e:
        click.echo(f"Scan failed: {e}", err=True)
        ctx.exit(1)

    # Select Reporter
    reporters = []

    # Always add console reporter unless we are in json mode only?
    # Usually CI logs want console output too.
    if reporter == 'console':
        reporters.append(ConsoleReporter())
    elif reporter == 'json':
        out_path = output or "codesage_report.json"
        reporters.append(JsonReporter(output_path=out_path))
    elif reporter == 'github':
        reporters.append(ConsoleReporter()) # Still print to console

        # Check environment
        token = os.environ.get("GITHUB_TOKEN")
        repo = os.environ.get("GITHUB_REPOSITORY")

        # Try to get PR number
        pr_number = None
        ref = os.environ.get("GITHUB_REF") # refs/pull/123/merge
        if ref and "pull" in ref:
            try:
                pr_number = int(ref.split("/")[2])
            except (IndexError, ValueError):
                pass

        # Or from event.json
        event_path = os.environ.get("GITHUB_EVENT_PATH")
        if not pr_number and event_path and os.path.exists(event_path):
            import json
            try:
                with open(event_path) as f:
                    event = json.load(f)
                    pr_number = event.get("pull_request", {}).get("number")
            except Exception:
                pass

        if token and repo and pr_number:
            reporters.append(GitHubPRReporter(token=token, repo=repo, pr_number=pr_number))
        else:
            click.echo("GitHub reporter selected but missing environment variables (GITHUB_TOKEN, GITHUB_REPOSITORY) or not in a PR context.", err=True)

    # CI Mode overrides
    if ci_mode and os.environ.get("GITHUB_ACTIONS") == "true":
         # In CI mode, we might force certain reporters or behavior
         pass

    # Execute Reporters
    for r in reporters:
        r.report(snapshot)

    # Check Fail Condition
    if fail_on_high:
        has_high_risk = False
        if snapshot.issues_summary:
            if snapshot.issues_summary.by_severity.get('high', 0) > 0 or \
               snapshot.issues_summary.by_severity.get('error', 0) > 0:
                has_high_risk = True

        # Also check risk summary if issues are not populated but risk is
        if snapshot.risk_summary and snapshot.risk_summary.high_risk_files > 0:
             has_high_risk = True

        if has_high_risk:
            click.echo("Failure: High risk issues detected.", err=True)
            ctx.exit(1)

    click.echo("Scan finished successfully.")
