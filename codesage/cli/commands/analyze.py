import click
import os
import pathspec
import json
import yaml
from datetime import datetime

from codesage.analyzers.parser_factory import create_parser
from codesage.cli.progress import create_progress_bar
from codesage.cli.formatter import format_table, colorize_complexity
from codesage.cli.validation import validate_path
from codesage.snapshot.models import ProjectSnapshot, SnapshotMetadata, FileSnapshot, ASTSummary, ComplexityMetrics, DependencyGraph
from codesage import __version__ as tool_version

def get_files_to_analyze(path, exclude):
    """Get a list of files to analyze, excluding specified patterns."""
    if os.path.isfile(path):
        return [path]

    spec = pathspec.PathSpec.from_lines('gitwildmatch', exclude)
    files_to_analyze = []
    for root, _, files in os.walk(path):
        for file in files:
            file_path = os.path.join(root, file)
            if not spec.match_file(file_path):
                files_to_analyze.append(file_path)
    return files_to_analyze

def _display_summary(results):
    """Display a summary of the analysis results."""
    total_files = len(results)
    total_lines = sum(r['lines'] for r in results)

    all_functions = []
    for r in results:
        all_functions.extend(r['functions'])

    avg_complexity = sum(f.complexity for f in all_functions) / len(all_functions) if all_functions else 0

    click.echo("\nAnalysis Summary")
    summary_data = [
        ("Total Files", total_files),
        ("Total Lines of Code", total_lines),
        ("Average Complexity", f"{avg_complexity:.2f}")
    ]
    click.echo(format_table(summary_data, ["Metric", "Value"]))

    hotspots = sorted(all_functions, key=lambda f: f.complexity, reverse=True)[:5]
    if hotspots:
        click.echo("\nComplexity Hotspots (Top 5)")
        hotspot_data = [
            (f.name, f.start_line, colorize_complexity(f.complexity, {}))
            for f in hotspots
        ]
        click.echo(format_table(hotspot_data, ["Function", "Line", "Complexity"]))

@click.command()
@click.argument('path', callback=validate_path)
@click.option('--language', '-l', help='Specify the language to analyze.')
@click.option('--exclude', '-e', multiple=True, help='File patterns to exclude.')
@click.option('--output', '-o', type=click.Path(), help='Output file path.')
@click.option('--format', '-f', type=click.Choice(['json', 'yaml']), default='json', help='Output format.')
@click.option('--no-progress', is_flag=True, help='Disable the progress bar.')
def analyze(path, language, exclude, output, format, no_progress):
    """Analyze a source code file or directory."""
    files_to_analyze = get_files_to_analyze(path, exclude)

    if not language:
        # A more robust auto-detection would be needed for a real application
        lang_map = {'.py': 'python', '.go': 'go'}
        ext = os.path.splitext(files_to_analyze[0])[1]
        language = lang_map.get(ext)
        if not language:
            click.echo("Could not determine language. Please specify with --language.", err=True)
            return

    parser = create_parser(language)
    analysis_results = []

    progress = create_progress_bar(len(files_to_analyze), "Analyzing files...")
    with progress:
        for file_path in progress.track(files_to_analyze):
            with open(file_path, 'r', errors='ignore') as f:
                source_code = f.read()

            parser.parse(source_code)
            functions = parser.extract_functions()
            imports = parser.extract_imports()

            analysis_results.append({
                "path": file_path,
                "language": language,
                "lines": len(source_code.splitlines()),
                "functions": functions,
                "imports": imports
            })

    _display_summary(analysis_results)

    if output:
        file_snapshots = [
            FileSnapshot(
                path=r['path'],
                language=r['language'],
                hash="", # Placeholder
                lines=r['lines'],
                ast_summary=ASTSummary(function_count=len(r['functions']), class_count=0, import_count=len(r['imports']), comment_lines=0),
                complexity_metrics=ComplexityMetrics(cyclomatic=0),
            ) for r in analysis_results
        ]

        snapshot = ProjectSnapshot(
            metadata=SnapshotMetadata(
                version="v1",
                timestamp=datetime.now(),
                tool_version=tool_version,
                config_hash="", # Placeholder
            ),
            files=file_snapshots,
            global_metrics={},
            dependency_graph=DependencyGraph(),
            detected_patterns=[],
            issues=[]
        )

        output_content = ""
        if format == 'json':
            output_content = snapshot.model_dump_json(indent=2)
        elif format == 'yaml':
            output_content = yaml.dump(snapshot.model_dump())

        with open(output, 'w') as f:
            f.write(output_content)
        click.echo(f"\nAnalysis results saved to {output}")
