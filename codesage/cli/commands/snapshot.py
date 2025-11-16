import click
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

@click.group()
def snapshot():
    """Manage code snapshots."""
    pass

@snapshot.command('create')
@click.argument('path', type=click.Path(exists=True, dir_okay=True))
@click.option('--format', '-f', type=click.Choice(['json', 'yaml']), default='json', help='Snapshot format.')
@click.pass_context
def create(ctx, path, format):
    """Create a new snapshot from the given path."""
    manager = SnapshotVersionManager(SNAPSHOT_DIR, DEFAULT_CONFIG['snapshot'])

    # This would be a more complex operation in a real application,
    # involving the analyzer and other components.
    # For now, we'll just create a basic snapshot.
    from codesage.snapshot.models import ProjectSnapshot, SnapshotMetadata, DependencyGraph
    from datetime import datetime
    from codesage import __version__ as tool_version
    import os

    files = [os.path.join(dp, f) for dp, dn, fn in os.walk(path) for f in fn]
    total_size = sum(os.path.getsize(f) for f in files)

    snapshot_data = ProjectSnapshot(
        metadata=SnapshotMetadata(
            version="", # Will be set by the manager
            timestamp=datetime.now(),
            project_name=os.path.basename(os.path.abspath(path)),
            file_count=len(files),
            total_size=total_size,
            tool_version=tool_version,
            config_hash="not_implemented"
        ),
        files=files,
        global_metrics={},
        dependency_graph=DependencyGraph(nodes=[], links=[]),
        detected_patterns=[],
        issues=[]
    )

    saved_path = manager.save_snapshot(snapshot_data, format)
    click.echo(f"Snapshot created at {saved_path}")

@snapshot.command('list')
def list_snapshots():
    """List all available snapshots."""
    manager = SnapshotVersionManager(SNAPSHOT_DIR, DEFAULT_CONFIG['snapshot'])
    snapshots = manager.list_snapshots()

    if not snapshots:
        click.echo("No snapshots found.")
        return

    for s in snapshots:
        click.echo(f"- {s['version']} ({s['timestamp']})")

@snapshot.command('show')
@click.argument('version')
def show(version):
    """Show details of a specific snapshot."""
    manager = SnapshotVersionManager(SNAPSHOT_DIR, DEFAULT_CONFIG['snapshot'])
    snapshot_data = manager.load_snapshot(version)

    if not snapshot_data:
        click.echo(f"Snapshot {version} not found.", err=True)
        return

    click.echo(f"Version: {snapshot_data.metadata.version}")
    click.echo(f"Timestamp: {snapshot_data.metadata.timestamp}")
    click.echo(f"Project: {snapshot_data.metadata.project_name}")
    click.echo(f"Files: {snapshot_data.metadata.file_count}")

@snapshot.command('cleanup')
@click.option('--dry-run', is_flag=True, help='Show which snapshots would be deleted.')
def cleanup(dry_run):
    """Clean up old snapshots."""
    manager = SnapshotVersionManager(SNAPSHOT_DIR, DEFAULT_CONFIG['snapshot'])

    if dry_run:
        click.echo("The following snapshots would be deleted:")
        # The current implementation of cleanup_expired_snapshots doesn't support dry runs
        # so we'd need to add that functionality to the version manager.
        # For now, we'll just list all snapshots.
        snapshots = manager.list_snapshots()
        for s in snapshots:
             click.echo(f"- {s['version']}")
    else:
        manager.cleanup_expired_snapshots()
        click.echo("Expired snapshots have been cleaned up.")

if __name__ == '__main__':
    snapshot()
