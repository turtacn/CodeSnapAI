from pathlib import Path

import click
import yaml
import json

from codesage.config.loader import load_config
from codesage.config.history import HistoryConfig
from codesage.history.trend_builder import build_trend_series

from codesage.audit.models import AuditEvent
from datetime import datetime

@click.command('history-trend', help="Generate trend data from historical snapshots.")
@click.option('--project-name', required=True, help="The name of the project.")
@click.option('--output', type=click.Path(dir_okay=False, writable=True), help="Path to save the trend output file.")
@click.option('--format', 'output_format', type=click.Choice(['json', 'yaml']), default='json', help="Output format.")
@click.option('--config-file', help="Path to the codesage config file.")
@click.pass_context
def history_trend_command(ctx, project_name, output, output_format, config_file):
    audit_logger = ctx.obj.audit_logger
    try:
        if config_file:
            raw_config = load_config(str(Path(config_file).parent))
        else:
            raw_config = load_config()

        history_config = HistoryConfig.model_validate(raw_config.get('history', {}))
        history_root = Path(history_config.history_root)

        trend_series = build_trend_series(history_root, project_name)

        data = trend_series.model_dump(mode='json')

        if output:
            with open(output, 'w', encoding='utf-8') as f:
                if output_format == 'json':
                    json.dump(data, f, indent=2)
                else:
                    yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
            click.echo(f"Trend data saved to {output}")
        else:
            if output_format == 'json':
                click.echo(json.dumps(data, indent=2))
            else:
                click.echo(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    finally:
        audit_logger.log(
            AuditEvent(
                timestamp=datetime.now(),
                event_type="cli.history_trend",
                project_name=project_name,
                command="history-trend",
                args={
                    "output": output,
                    "output_format": output_format,
                    "config_file": config_file,
                },
            )
        )
