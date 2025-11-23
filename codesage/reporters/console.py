from .base import BaseReporter
from codesage.snapshot.models import ProjectSnapshot
import click

class ConsoleReporter(BaseReporter):
    def report(self, snapshot: ProjectSnapshot) -> None:
        click.echo("Scan Complete")

        # Summary
        click.echo("-" * 40)
        click.echo(f"Project: {snapshot.metadata.project_name}")
        click.echo(f"Files Scanned: {len(snapshot.files)}")

        if snapshot.issues_summary:
            click.echo(f"Total Issues: {snapshot.issues_summary.total_issues}")
            for severity, count in snapshot.issues_summary.by_severity.items():
                click.echo(f"  {severity.upper()}: {count}")
        else:
            click.echo("No issues summary available.")

        if snapshot.risk_summary:
            click.echo(f"Risk Score: {snapshot.risk_summary.avg_risk:.2f}")
            click.echo(f"High Risk Files: {snapshot.risk_summary.high_risk_files}")

        click.echo("-" * 40)

        # Detail for High/Error issues
        if snapshot.issues_summary and snapshot.issues_summary.total_issues > 0:
            click.echo("\nTop Issues:")
            count = 0
            for file in snapshot.files:
                for issue in file.issues:
                    if issue.severity in ['error', 'warning', 'high']:
                        click.echo(f"[{issue.severity.upper()}] {file.path}:{issue.location.line} - {issue.message}")
                        count += 1
                        if count >= 10:
                            click.echo("... and more")
                            return
