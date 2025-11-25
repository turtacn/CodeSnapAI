from datetime import datetime
from pathlib import Path
import click
import yaml

from codesage.config.loader import load_config
from codesage.config.history import HistoryConfig
from codesage.history.models import HistoricalSnapshot, SnapshotMeta
from codesage.history.store import save_historical_snapshot, update_snapshot_index
from codesage.snapshot.models import ProjectSnapshot

from codesage.audit.models import AuditEvent

@click.command('history-snapshot', help="Save a snapshot to the history store.")
@click.option('--snapshot', 'snapshot_path', required=True, type=click.Path(exists=True, dir_okay=False), help="Path to the project snapshot YAML file.")
@click.option('--project-name', required=True, help="The name of the project.")
@click.option('--commit', help="The git commit hash.")
@click.option('--branch', help="The git branch name.")
@click.option('--trigger', default='manual', help="The trigger for the snapshot (e.g., 'ci', 'manual').")
@click.option('--config-file', help="Path to the codesage config file.")
@click.pass_context
def history_snapshot(ctx, snapshot_path, project_name, commit, branch, trigger, config_file):
    audit_logger = ctx.obj.audit_logger
    try:
        if config_file:
            raw_config = load_config(str(Path(config_file).parent))
        else:
            raw_config = load_config()

        history_config = HistoryConfig.model_validate(raw_config.get('history', {}))
        history_root = Path(history_config.history_root)

        with open(snapshot_path, 'r', encoding='utf-8') as f:
            snapshot_data = yaml.safe_load(f)

        project_snapshot = ProjectSnapshot.model_validate(snapshot_data)

        snapshot_id = commit or datetime.utcnow().strftime('%Y%m%d%H%M%S')

        meta = SnapshotMeta(
            project_name=project_name,
            snapshot_id=snapshot_id,
            # commit=commit, # SnapshotMeta in models.py doesn't have commit/branch/trigger in my recent update or memory?
            # Let's check model definition.
            # SnapshotMeta(snapshot_id, created_at, project_name)
            created_at=datetime.utcnow()
        )

        hs = HistoricalSnapshot(meta=meta, snapshot=project_snapshot)

        save_historical_snapshot(history_root, hs, history_config)
        update_snapshot_index(history_root, meta, max_snapshots=history_config.max_snapshots)

        click.echo(f"Successfully saved snapshot with id '{snapshot_id}' for project '{project_name}'.")
    except Exception as e:
        # Log the exception details for debugging tests
        click.echo(f"Error: {e}")
        raise e
    finally:
        audit_logger.log(
            AuditEvent(
                timestamp=datetime.now(),
                event_type="cli.history_snapshot",
                project_name=project_name,
                command="history-snapshot",
                args={
                    "snapshot_path": snapshot_path,
                    "commit": commit,
                    "branch": branch,
                    "trigger": trigger,
                    "config_file": config_file,
                },
            )
        )
