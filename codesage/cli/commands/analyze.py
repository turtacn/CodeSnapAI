import click
import os
import fnmatch
import json
import yaml
from codesage.analyzers.parser_factory import create_parser

LANGUAGE_EXTENSIONS = {
    "python": {".py", ".pyw"},
    "go": {".go"},
}

DEFAULT_EXCLUDE_DIRS = {
    ".git", ".svn", ".hg", "CVS",
    ".vscode", ".idea",
    "__pycache__", "node_modules", "vendor", "dist", "build", "target",
}

@click.command()
@click.argument('path', type=click.Path(exists=True, file_okay=True, dir_okay=True, readable=True))
@click.option('--language', '-l', help='Specify the language to analyze.')
@click.option('--exclude', '-e', multiple=True, help='File patterns to exclude.')
@click.option('--output', '-o', type=click.Path(), help='Output file path.')
@click.option('--format', '-f', type=click.Choice(['json', 'markdown', 'yaml']), default='json', help='Output format.')
@click.option('--no-progress', is_flag=True, help='Disable the progress bar.')
def analyze(path, language, exclude, output, format, no_progress):
    """
    Analyze a source code file or directory.
    """
    if os.path.isfile(path):
        files_to_analyze = [path]
    else:
        files_to_analyze = []
        exclude_patterns = list(exclude)

        for root, dirs, files in os.walk(path, topdown=True):
            dirs[:] = [d for d in dirs if d not in DEFAULT_EXCLUDE_DIRS]

            for file in files:
                file_path = os.path.join(root, file)

                if any(fnmatch.fnmatch(file_path, pattern) for pattern in exclude_patterns):
                    continue

                if language:
                    allowed_extensions = LANGUAGE_EXTENSIONS.get(language, set())
                    if not any(file.endswith(ext) for ext in allowed_extensions):
                        continue

                files_to_analyze.append(file_path)

    if not language:
        if files_to_analyze and files_to_analyze[0].endswith('.py'):
            language = 'python'
        elif files_to_analyze and files_to_analyze[0].endswith('.go'):
            language = 'go'
        else:
            click.echo("Could not determine language. Please specify with --language.", err=True)
            return

    try:
        parser = create_parser(language)
    except ValueError as e:
        click.echo(e, err=True)
        return

    analysis_results = []
    for file_path in files_to_analyze:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            source_code = f.read()

        parser.parse(source_code)

        if parser.tree and parser.tree.root_node.has_error:
            click.echo(f"Warning: Skipping file {file_path} due to syntax errors.", err=True)
            continue

        imports = parser.extract_imports()
        ast_summary = parser.get_ast_summary(source_code)
        complexity_metrics = parser.get_complexity_metrics(source_code)

        file_result = {
            "file_path": file_path,
            "lines": len(source_code.splitlines()),
            "complexity": complexity_metrics.cyclomatic,
            "imports": [i.path for i in imports],
            "functions": ast_summary.function_count,
        }
        analysis_results.append(file_result)

    if output:
        if format == 'json':
            with open(output, 'w') as f:
                json.dump(analysis_results, f, indent=2)
        elif format == 'yaml':
            with open(output, 'w') as f:
                yaml.dump(analysis_results, f)
        elif format == 'markdown':
            with open(output, 'w') as f:
                for result in analysis_results:
                    f.write(f"## {result['file_path']}\n\n")
                    f.write(f"- **Lines of code:** {result['lines']}\n")
                    f.write(f"- **Cyclomatic complexity:** {result['complexity']}\n")
                    f.write(f"- **Functions:** {result['functions']}\n\n")
                    f.write("### Imports\n\n")
                    for imp in result['imports']:
                        f.write(f"- `{imp}`\n")
                    f.write("\n")
        click.echo(f"Analysis results saved to {output}")
    else:
        for result in analysis_results:
            click.echo(f"File: {result['file_path']}")
            click.echo(f"  Lines: {result['lines']}")
            click.echo(f"  Complexity: {result['complexity']}")
            click.echo(f"  Functions: {result['functions']}")
            click.echo(f"  Imports: {result['imports']}")

if __name__ == '__main__':
    analyze()
