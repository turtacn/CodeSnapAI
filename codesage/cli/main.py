import click
from codesage import __version__

# Placeholder for commands
from .commands.analyze import analyze
from .commands.snapshot import snapshot
from .commands.diff import diff
from .commands.config import config
from .commands.report import report
from .commands.llm_suggest import llm_suggest
from .plugin_loader import load_plugins

@click.group(context_settings=dict(help_option_names=['-h', '--help']))
@click.option('--config', type=click.Path(), help='配置文件路径')
@click.option('--verbose', '-v', is_flag=True, help='详细输出')
@click.option('--no-color', is_flag=True, help='禁用彩色输出')
@click.version_option(version=__version__)
def main(config, verbose, no_color):
    """
    CodeSage: An intelligent code analysis tool.
    """
    pass

main.add_command(analyze)
main.add_command(snapshot)
main.add_command(diff)
main.add_command(config)
main.add_command(report)
main.add_command(llm_suggest)

# Load plugin commands
load_plugins(main)

if __name__ == '__main__':
    main()
