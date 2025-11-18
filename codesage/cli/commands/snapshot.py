import click
import os
import json
import gzip
import hashlib
from datetime import datetime
from pathlib import Path

from codesage.snapshot.versioning import SnapshotVersionManager
from codesage.snapshot.models import ProjectSnapshot, SnapshotMetadata, FileSnapshot, ASTSummary, ComplexityMetrics, DependencyGraph
from codesage.analyzers.parser_factory import create_parser
from codesage import __version__ as tool_version
from codesage.semantic_digest.python_snapshot_builder import PythonSemanticSnapshotBuilder, SnapshotConfig
from codesage.snapshot.yaml_generator import YAMLGenerator

DEFAULT_EXCLUDE_DIRS = {
    ".git", ".svn", ".hg", "CVS",
    ".vscode", ".idea",
    "__pycache__", "node_modules", "vendor", "dist", "build", "target",
}

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

def detect_language(file_path):
    _, extension = os.path.splitext(file_path)
    if extension == '.py':
        return 'python'
    elif extension == '.go':
        return 'go'
    return None

@click.group()
def snapshot():
    """Manage code snapshots."""
    pass

from codesage.semantic_digest.go_snapshot_builder import GoSemanticSnapshotBuilder
from codesage.semantic_digest.shell_snapshot_builder import ShellSemanticSnapshotBuilder


@snapshot.command('create')
@click.argument('path', type=click.Path(exists=True, dir_okay=True))
@click.option('--format', '-f', type=click.Choice(['json', 'python-semantic-digest']), default='json', help='Snapshot format.')
@click.option('--output', '-o', type=click.Path(), default=None, help='Output file path.')
@click.option('--compress', is_flag=True, help='Enable compression.')
@click.option('--language', '-l', type=click.Choice(['python', 'go', 'shell', 'auto']), default='python', help='Language to analyze.')
def create(path, format, output, compress, language):
    """Create a new snapshot from the given path."""
    root_path = Path(path)

    if format == 'python-semantic-digest':
        if output is None:
            output = f"{root_path.name}_{language}_semantic_digest.yaml"

        config = SnapshotConfig()
        if language == 'python':
            builder = PythonSemanticSnapshotBuilder(root_path, config)
        elif language == 'go':
            builder = GoSemanticSnapshotBuilder(root_path, config)
        elif language == 'shell':
            builder = ShellSemanticSnapshotBuilder(root_path, config)
        elif language == 'auto':
            # In a real implementation, this would involve more sophisticated logic
            # to detect languages and combine snapshots.
            click.echo("Auto language detection is not yet implemented.")
            return
        else:
            click.echo(f"Unsupported language: {language}", err=True)
            return

        project_snapshot = builder.build()

        generator = YAMLGenerator()
        generator.export(project_snapshot, Path(output))

        click.echo(f"{language.capitalize()} semantic digest created at {output}")
        return

    manager = SnapshotVersionManager(SNAPSHOT_DIR, DEFAULT_CONFIG['snapshot'])

    file_snapshots = []
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in DEFAULT_EXCLUDE_DIRS]
        for file in files:
            file_path = os.path.join(root, file)
            language = detect_language(file_path)

            if language:
                parser = create_parser(language)
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    source_code = f.read()

                ast_summary = parser.get_ast_summary(source_code)
                complexity_metrics = parser.get_complexity_metrics(source_code)
            else:
                language = "unknown"
                ast_summary=ASTSummary(function_count=0, class_count=0, import_count=0, comment_lines=0)
                complexity_metrics=ComplexityMetrics(cyclomatic=0)

            file_snapshots.append(FileSnapshot(
                path=file_path,
                language=language,
                hash=get_file_hash(file_path),
                lines=len(open(file_path, encoding='utf-8', errors='ignore').readlines()),
                ast_summary=ast_summary,
                complexity_metrics=complexity_metrics,
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
        dependency_graph=DependencyGraph(edges=[]),
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
