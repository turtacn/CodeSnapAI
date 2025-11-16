import click
import json
from codesage.snapshot.versioning import SnapshotVersionManager
from codesage.snapshot.differ import SnapshotDiffer
from codesage.cli.formatter import format_table

DEFAULT_CONFIG = {
    "snapshot": {
        "versioning": {
            "max_versions": 10,
            "retention_days": 30
        }
    }
}
SNAPSHOT_DIR = ".codesage/snapshots"

def _display_diff_summary(diff_data, version1, version2):
    """Displays a formatted summary of the snapshot diff."""
    click.echo(f"\nComparing {version1} and {version2}")

    summary_data = [
        ("Added Files", len(diff_data.added_files)),
        ("Removed Files", len(diff_data.removed_files)),
        ("Modified Files", len(diff_data.modified_files)),
    ]
    click.echo(format_table(summary_data, ["Metric", "Value"]))

    if diff_data.added_files:
        click.echo("\nAdded Files:")
        for f in diff_data.added_files:
            click.echo(f"  [green]+ {f}[/green]")

    if diff_data.removed_files:
        click.echo("\nRemoved Files:")
        for f in diff_data.removed_files:
            click.echo(f"  [red]- {f}[/red]")

    if diff_data.modified_files:
        click.echo("\nModified Files:")
        modified_data = [
            (f.path, f.complexity_delta)
            for f in diff_data.modified_files
        ]
        click.echo(format_table(modified_data, ["File", "Complexity Delta"]))

@click.command()
@click.argument('version1')
@click.argument('version2')
@click.option('--output', '-o', type=click.Path(), help='Output file for the diff report.')
@click.option('--format', '-f', type=click.Choice(['json']), default='json', help='Output format.')
def diff(version1, version2, output, format):
    """Compare two snapshots and show the differences."""
    manager = SnapshotVersionManager(SNAPSHOT_DIR, DEFAULT_CONFIG['snapshot'])

    snapshot1 = manager.load_snapshot(version1)
    if not snapshot1:
        click.echo(f"Snapshot '{version1}' not found.", err=True)
        return

    snapshot2 = manager.load_snapshot(version2)
    if not snapshot2:
        click.echo(f"Snapshot '{version2}' not found.", err=True)
        return

    differ = SnapshotDiffer()
    diff_data = differ.diff(snapshot1, snapshot2)

    _display_diff_summary(diff_data, version1, version2)

    if output:
        if format == 'json':
            # Pydantic models need to be converted to dicts for JSON serialization
            from pydantic import BaseModel
            class DiffEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, BaseModel):
                        return obj.model_dump()
                    return super().default(obj)

            with open(output, 'w') as f:
                json.dump(diff_data, f, indent=2, cls=DiffEncoder)
            click.echo(f"\nDiff report saved to {output}")
