import click
import os
import fnmatch
from codesage.analyzers.parser_factory import create_parser

DEFAULT_EXCLUDE_DIRS = {
    ".git", ".svn", ".hg", "CVS",
    ".vscode", ".idea",
    "__pycache__", "node_modules", "vendor", "dist", "build", "target",
}

BINARY_EXTENSIONS = {
    # Images
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".svg",
    # Archives
    ".zip", ".tar", ".gz", ".rar", ".7z",
    # Documents
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    # Executables/libs
    ".exe", ".dll", ".so", ".a", ".o", ".jar", ".class",
    # Other
    ".lock",
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
            # Exclude directories
            dirs[:] = [d for d in dirs if d not in DEFAULT_EXCLUDE_DIRS]

            for file in files:
                file_path = os.path.join(root, file)

                # Exclude based on patterns
                if any(fnmatch.fnmatch(file_path, pattern) for pattern in exclude_patterns):
                    continue

                # Exclude binary files
                if os.path.splitext(file)[1].lower() in BINARY_EXTENSIONS:
                    continue

                files_to_analyze.append(file_path)

    if not language:
        # Simple auto-detection for now.
        if files_to_analyze[0].endswith('.py'):
            language = 'python'
        elif files_to_analyze[0].endswith('.go'):
            language = 'go'
        else:
            click.echo("Could not determine language. Please specify with --language.", err=True)
            return

    try:
        parser = create_parser(language)
    except ValueError as e:
        click.echo(e, err=True)
        return

    for file_path in files_to_analyze:
        # TODO: Add progress bar here.
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            source_code = f.read()

        parser.parse(source_code)
        functions = parser.extract_functions()
        imports = parser.extract_imports()

        click.echo(f"File: {file_path}")
        click.echo(f"  Imports: {[i.path for i in imports]}")
        click.echo(f"  Functions: {[f.name for f in functions]}")

if __name__ == '__main__':
    analyze()
