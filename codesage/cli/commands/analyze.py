import click
import os
from codesage.analyzers.parser_factory import create_parser

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
        for root, _, files in os.walk(path):
            for file in files:
                files_to_analyze.append(os.path.join(root, file))

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
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()

        parser.parse(source_code)
        functions = parser.extract_functions()
        imports = parser.extract_imports()

        click.echo(f"File: {file_path}")
        click.echo(f"  Imports: {[i.name for i in imports]}")
        click.echo(f"  Functions: {[f.name for f in functions]}")

if __name__ == '__main__':
    analyze()
