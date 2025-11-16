import click
import os
import json
import gzip
import hashlib
from datetime import datetime
from codesage.snapshot.versioning import SnapshotVersionManager
from codesage.snapshot.models import ProjectSnapshot, SnapshotMetadata, FileSnapshot, ASTSummary, ComplexityMetrics, DependencyGraph
from codesage import __version__ as tool_version

DEFAULT_CONFIG = {
    "snapshot": {
        "versioning": {
            "max_versions": 10,
            "retention_days": 30
        }
    }
}
SNAPSHOT_DIR = ".codesage/snapshots"

def get_file_hash(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

@click.group()
def snapshot():
    """Manage code snapshots."""
    pass

@snapshot.command('create')
@click.argument('path', type=click.Path(exists=True, dir_okay=True))
@click.option('--format', '-f', type=click.Choice(['json']), default='json', help='Snapshot format.')
@click.option('--compress', is_flag=True, help='Enable compression.')
def create(path, format, compress):
    """Create a new snapshot from the given path."""
    manager = SnapshotVersionManager(SNAPSHOT_DIR, DEFAULT_CONFIG['snapshot'])

    file_snapshots = []
    for root, _, files in os.walk(path):
        for file in files:
            file_path = os.path.join(root, file)
            file_snapshots.append(FileSnapshot(
                path=file_path,
                language="python",  # Dummy value
                hash=get_file_hash(file_path),
                lines=len(open(file_path).readlines()),
                ast_summary=ASTSummary(function_count=0, class_count=0, import_count=0, comment_lines=0),
                complexity_metrics=ComplexityMetrics(cyclomatic=0),
            ))

    total_size = sum(os.path.getsize(fs.path) for fs in file_snapshots)

    snapshot_data = ProjectSnapshot(
        metadata=SnapshotMetadata(
            version="",
            timestamp=datetime.now(),
            project_name=os.path.basename(os.path.abspath(path)),
            file_count=len(file_snapshots),
            total_size=total_size,
            tool_version=tool_version,
            config_hash="not_implemented",
            git_commit=None
        ),
        files=file_snapshots,
        global_metrics={},
        dependency_graph=DependencyGraph(nodes=[], links=[]),
        detected_patterns=[],
        issues=[]
    )

    if compress:
        snapshot_path = manager.save_snapshot(snapshot_data, format)
        with open(snapshot_path, 'rb') as f_in:
            with gzip.open(f"{snapshot_path}.gz", 'wb') as f_out:
                f_out.writelines(f_in)
        os.remove(snapshot_path)
        click.echo(f"Compressed snapshot created at {snapshot_path}.gz")
    else:
        snapshot_path = manager.save_snapshot(snapshot_data, format)
        click.echo(f"Snapshot created at {snapshot_path}")

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
    click.echo(snapshot_data.model_dump_json(indent=2))

@snapshot.command('cleanup')
@click.option('--dry-run', is_flag=True, help='Show which snapshots would be deleted.')
def cleanup(dry_run):
    """Clean up old snapshots."""
    from datetime import timedelta

    manager = SnapshotVersionManager(SNAPSHOT_DIR, DEFAULT_CONFIG['snapshot'])

    if dry_run:
        index = manager._load_index()
        now = datetime.now()

        expired_by_date = [
            s for s in index
            if now - datetime.fromisoformat(s["timestamp"]) > timedelta(days=manager.retention_days)
        ]

        sorted_by_date = sorted(index, key=lambda s: s["timestamp"], reverse=True)
        expired_by_count = sorted_by_date[manager.max_versions:]

        expired = {s['version']: s for s in expired_by_date + expired_by_count}.values()

        if not expired:
            click.echo("No snapshots to clean up.")
            return

        click.echo("Snapshots to be deleted:")
        for s in expired:
            click.echo(f"- {s['version']}")
    else:
        manager.cleanup_expired_snapshots()
        click.echo("Expired snapshots have been cleaned up.")
