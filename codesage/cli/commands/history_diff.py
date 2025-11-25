from pathlib import Path

import click
import yaml

from codesage.config.loader import load_config
from codesage.config.history import HistoryConfig
from codesage.history.diff_engine import diff_project_snapshots
from codesage.history.store import load_historical_snapshot


from codesage.audit.models import AuditEvent
from datetime import datetime

@click.command('history-diff', help="Compare two historical snapshots.")
@click.option('--project-name', required=True, help="The name of the project.")
@click.option('--from-id', required=True, help="The ID of the 'before' snapshot.")
@click.option('--to-id', required=True, help="The ID of the 'after' snapshot.")
@click.option('--output', type=click.Path(dir_okay=False, writable=True), help="Path to save the diff output YAML file.")
@click.option('--config-file', help="Path to the codesage config file.")
@click.pass_context
def history_diff(ctx, project_name, from_id, to_id, output, config_file):
    audit_logger = ctx.obj.audit_logger
    try:
        if config_file:
            raw_config = load_config(str(Path(config_file).parent))
        else:
            raw_config = load_config()

        history_config = HistoryConfig.model_validate(raw_config.get('history', {}))
        history_root = Path(history_config.history_root)

        hs_old = load_historical_snapshot(history_root, project_name, from_id)
        hs_new = load_historical_snapshot(history_root, project_name, to_id)

        diff_summary, file_diffs = diff_project_snapshots(
            hs_old.snapshot, hs_new.snapshot, from_id, to_id
        )

        data = {
            "project_diff": diff_summary.model_dump(mode='json'),
            "file_diffs": [fd.model_dump(mode='json') for fd in file_diffs],
        }

        if output:
            with open(output, 'w', encoding='utf-8') as f:
                yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
            click.echo(f"Diff report saved to {output}")
        else:
            click.echo(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    finally:
        audit_logger.log(
            AuditEvent(
                timestamp=datetime.now(),
                event_type="cli.history_diff",
                project_name=project_name,
                command="history-diff",
                args={
                    "from_id": from_id,
                    "to_id": to_id,
                    "output": output,
                    "config_file": config_file,
                },
            )
        )
