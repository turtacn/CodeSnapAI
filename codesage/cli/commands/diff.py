import click
from codesage.snapshot.versioning import SnapshotVersionManager
from codesage.snapshot.differ import SnapshotDiffer

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

@click.command()
@click.argument('version1')
@click.argument('version2')
@click.option('--output', '-o', type=click.Path(), help='Output file for the diff report.')
@click.option('--format', '-f', type=click.Choice(['json', 'markdown']), default='json', help='Output format.')
def diff(version1, version2, output, format):
    """
    Compare two snapshots and show the differences.
    """
    manager = SnapshotVersionManager(SNAPSHOT_DIR, DEFAULT_CONFIG['snapshot'])

    snapshot1 = manager.load_snapshot(version1)
    if not snapshot1:
        click.echo(f"Snapshot {version1} not found.", err=True)
        return

    snapshot2 = manager.load_snapshot(version2)
    if not snapshot2:
        click.echo(f"Snapshot {version2} not found.", err=True)
        return

    differ = SnapshotDiffer()
    diff_data = differ.diff(snapshot1, snapshot2)

    if output:
        # TODO: Implement file output
        click.echo(f"Diff report will be saved to {output} in {format} format.")

    click.echo(f"Comparing {version1} and {version2}:")
    click.echo(f"  Added files: {len(diff_data.added_files)}")
    click.echo(f"  Removed files: {len(diff_data.removed_files)}")
    click.echo(f"  Modified files: {len(diff_data.modified_files)}")
    click.echo(f"  Added dependencies: {len(diff_data.dependency_changes.added_edges)}")
    click.echo(f"  Removed dependencies: {len(diff_data.dependency_changes.removed_edges)}")


if __name__ == '__main__':
    diff()
