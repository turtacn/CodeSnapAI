import click
from codesage.snapshot.versioning import SnapshotVersionManager
from codesage.cli.commands.analyze import analyze
import json

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
@click.pass_context
@click.option('--path', default='.', help='Path to the code to analyze.')
@click.option('--language', '-l', help='Specify the language to analyze.')
@click.option('--exclude', '-e', multiple=True, help='File patterns to exclude.')
def create(ctx, path, language, exclude):
    """Create a new snapshot."""
    manager = SnapshotVersionManager(SNAPSHOT_DIR, DEFAULT_CONFIG['snapshot'])

    # Programmatically invoke the analyze command
    # We'll use a temporary file to get the snapshot data
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w+', delete=True, suffix='.json') as tmp:
        try:
            ctx.invoke(
                analyze,
                path=path,
                language=language,
                exclude=exclude,
                output=tmp.name,
                format='json',
                no_progress=True
            )
            tmp.seek(0)
            snapshot_data = json.load(tmp)
        except Exception as e:
            click.echo(f"An error occurred during analysis: {e}", err=True)
            return

    from codesage.snapshot.models import ProjectSnapshot
    snapshot_obj = ProjectSnapshot.model_validate(snapshot_data)

    saved_path = manager.save_snapshot(snapshot_obj)
    click.echo(f"\nSnapshot '{snapshot_obj.metadata.version}' saved to {saved_path}")

@snapshot.command('list')
def list_snapshots():
    """List all available snapshots."""
    manager = SnapshotVersionManager(SNAPSHOT_DIR, DEFAULT_CONFIG['snapshot'])
    snapshots = manager.list_snapshots()

    if not snapshots:
        click.echo("No snapshots found.")
        return

    from codesage.cli.formatter import format_table
    table_data = [[s['version'], s['timestamp'], s.get('git_commit', 'N/A')] for s in snapshots]
    click.echo(format_table(table_data, ["Version", "Timestamp", "Git Commit"]))

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
    click.echo(f"Files: {len(snapshot_data.files)}")

    from codesage.cli.formatter import format_table
    file_data = [[f.path, f.language, f.lines] for f in snapshot_data.files[:10]]
    click.echo("\nFiles (first 10):")
    click.echo(format_table(file_data, ["Path", "Language", "Lines"]))

@snapshot.command('cleanup')
@click.option('--dry-run', is_flag=True, help='Show which snapshots would be deleted.')
def cleanup(dry_run):
    """Clean up old snapshots."""
    # This needs a more robust implementation in the version manager
    click.echo("Cleanup command is not fully implemented yet.")

if __name__ == '__main__':
    snapshot()
