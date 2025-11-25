import click
from codesage import __version__

# Placeholder for commands
from .commands.analyze import analyze
from .commands.snapshot import snapshot
from .commands.scan import scan
from .commands.diff import diff
from .commands.config import config
from .commands.report import report
from .commands.llm_suggest import llm_suggest
from .commands.governance_plan import governance_plan
from .commands.jules_prompt import jules_prompt
from .commands.web_console import web_console
from .commands.history_snapshot import history_snapshot
from .commands.history_diff import history_diff
from .commands.history_trend import history_trend
from .commands.org_report import org_report
from .plugin_loader import load_plugins

from codesage.config.loader import load_config
from codesage.config.audit import AuditConfig
from codesage.audit.logger import AuditLogger
from pathlib import Path

class CliContext:
    def __init__(self, audit_logger: AuditLogger):
        self.audit_logger = audit_logger

@click.group(context_settings=dict(help_option_names=['-h', '--help']))
@click.option('--config', 'config_path', type=click.Path(), help='配置文件路径')
@click.option('--verbose', '-v', is_flag=True, help='详细输出')
@click.option('--no-color', is_flag=True, help='禁用彩色输出')
@click.version_option(version=__version__)
@click.pass_context
def main(ctx, config_path, verbose, no_color):
    """
    CodeSage: An intelligent code analysis tool.
    """
    project_path = Path(config_path).parent if config_path else Path.cwd()
    raw_config = load_config(str(project_path))

    audit_config = AuditConfig(**raw_config.get('audit', {}))
    try:
        audit_logger = AuditLogger(audit_config)
    except PermissionError:
        audit_logger = AuditLogger(AuditConfig(enabled=False))

    ctx.obj = CliContext(audit_logger=audit_logger)

main.add_command(analyze)
main.add_command(snapshot)
main.add_command(scan)
main.add_command(diff)
main.add_command(config)
main.add_command(report)
main.add_command(llm_suggest)
main.add_command(governance_plan)
main.add_command(jules_prompt)
main.add_command(web_console)
main.add_command(history_snapshot)
main.add_command(history_diff)
main.add_command(history_trend)
main.add_command(org_report)

# Load plugin commands
load_plugins(main)

if __name__ == '__main__':
    main()
