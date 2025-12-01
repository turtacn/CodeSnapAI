import click
import os
import json
import gzip
import hashlib
from datetime import datetime, timezone
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

from codesage.config.defaults import SNAPSHOT_DIR, DEFAULT_SNAPSHOT_CONFIG

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
from codesage.semantic_digest.java_snapshot_builder import JavaSemanticSnapshotBuilder


from codesage.audit.models import AuditEvent


def _create_snapshot_data(path, project_name):
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

    return ProjectSnapshot(
        metadata=SnapshotMetadata(
            version="",
            timestamp=datetime.now(),
            project_name=project_name,
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

@snapshot.command('create')
@click.argument('path', type=click.Path(exists=True, dir_okay=True))
@click.option('--project', '-p', 'project_name_override', help='Override the project name.')
@click.option('--format', '-f', type=click.Choice(['yaml', 'json', 'md']), default='yaml', help='Snapshot format.')
@click.option('--output', '-o', type=click.Path(), default=None, help='Output file path.')
@click.option('--compress', is_flag=True, help='Enable compression.')
@click.option('--language', '-l', type=click.Choice(['python', 'go', 'shell', 'java', 'auto']), default='auto', help='Language to analyze.')
@click.pass_context
def create(ctx, path, project_name_override, format, output, compress, language):
    """Create a new snapshot from the given path."""
    audit_logger = ctx.obj.audit_logger
    project_name = project_name_override or os.path.basename(os.path.abspath(path))
    try:
        root_path = Path(path)

        if language == 'auto':
            if list(root_path.rglob("*.py")):
                language = "python"
            elif list(root_path.rglob("*.go")):
                language = "go"
            elif list(root_path.rglob("*.java")):
                language = "java"
            elif list(root_path.rglob("*.sh")):
                language = "shell"
            else:
                click.echo("Could not auto-detect language.", err=True)
                return

        if language in ['python', 'go']:
            config = SnapshotConfig()
            builder = None
            if language == 'python':
                builder = PythonSemanticSnapshotBuilder(root_path, config)
            else: # language == 'go'
                builder = GoSemanticSnapshotBuilder(root_path, config)

            project_snapshot = builder.build()

            if output is None:
                output = f"{root_path.name}_snapshot.{format}"

            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if format == 'yaml':
                generator = YAMLGenerator()
                generator.export(project_snapshot, output_path)
            elif format == 'json':
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(project_snapshot, f, indent=2)
            elif format == 'md':
                click.echo("Markdown format is not yet implemented.", err=True)
                return

            click.echo(f"Snapshot created at {output}")

        else: # Fallback to original snapshot logic for other languages
            snapshot_data = _create_snapshot_data(path, project_name)

            if output:
                output_path = Path(output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(snapshot_data.model_dump_json(indent=2))
                click.echo(f"Snapshot created at {output}")
            else:
                manager = SnapshotVersionManager(SNAPSHOT_DIR, project_name, DEFAULT_SNAPSHOT_CONFIG['snapshot'])
                save_format = 'json'
                if compress:
                    snapshot_path = manager.save_snapshot(snapshot_data, save_format)
                    with open(snapshot_path, 'rb') as f_in:
                        with gzip.open(f"{snapshot_path}.gz", 'wb') as f_out:
                            f_out.writelines(f_in)
                    os.remove(snapshot_path)
                    click.echo(f"Compressed snapshot created at {snapshot_path}.gz")
                else:
                    snapshot_path = manager.save_snapshot(snapshot_data, save_format)
                    click.echo(f"Snapshot created at {snapshot_path}")
    finally:
        audit_logger.log(
            AuditEvent(
                timestamp=datetime.now(timezone.utc),
                event_type="cli.snapshot.create",
                project_name=project_name,
                command="snapshot create",
                args={
                    "path": path,
                    "format": format,
                    "output": output,
                    "compress": compress,
                    "language": language,
                },
            )
        )

@snapshot.command('list')
@click.option('--project', '-p', required=True, help='The name of the project.')
def list_snapshots(project):
    """List all available snapshots for a project."""
    manager = SnapshotVersionManager(SNAPSHOT_DIR, project, DEFAULT_SNAPSHOT_CONFIG['snapshot'])
    snapshots = manager.list_snapshots()
    if not snapshots:
        click.echo(f"No snapshots found for project '{project}'.")
        return
    for s in snapshots:
        click.echo(f"- {s['version']} ({s['timestamp']})")

@snapshot.command('show')
@click.argument('version')
@click.option('--project', '-p', required=True, help='The name of the project.')
def show(version, project):
    """Show details of a specific snapshot."""
    manager = SnapshotVersionManager(SNAPSHOT_DIR, project, DEFAULT_SNAPSHOT_CONFIG['snapshot'])
    snapshot_data = manager.load_snapshot(version)
    if not snapshot_data:
        click.echo(f"Snapshot {version} not found for project '{project}'.", err=True)
        return
    click.echo(snapshot_data.model_dump_json(indent=2))

@snapshot.command('cleanup')
@click.option('--project', '-p', required=True, help='The name of the project.')
@click.option('--keep', type=int, default=None, help='Number of recent snapshots to keep.')
@click.option('--dry-run', is_flag=True, help='Show which snapshots would be deleted.')
def cleanup(project, keep, dry_run):
    """Clean up old snapshots for a project."""
    config_override = DEFAULT_SNAPSHOT_CONFIG['snapshot'].copy()
    if keep is not None:
        config_override['versioning']['max_versions'] = keep

    manager = SnapshotVersionManager(SNAPSHOT_DIR, project, config_override)

    if dry_run:
        index = manager._load_index()
        if not index:
            click.echo(f"No snapshots to clean up for project '{project}'.")
            return

        now = datetime.now(timezone.utc)
        expired_snapshots = manager._get_expired_snapshots(index, now)

        if not expired_snapshots:
            click.echo(f"No snapshots to clean up for project '{project}'.")
            return

        click.echo("Snapshots to be deleted:")
        for s in expired_snapshots:
            click.echo(f"- {s['version']}")
    else:
        deleted_count = manager.cleanup_expired_snapshots()
        click.echo(f"Cleaned up {deleted_count} expired snapshots for project '{project}'.")
