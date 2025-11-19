import click
import uvicorn
from typing import Optional

from codesage.config.loader import load_config
from codesage.config.web import WebConsoleConfig
from codesage.web.server import create_app

from codesage.audit.models import AuditEvent
from datetime import datetime

@click.command("web-console")
@click.option("--config", "config_path", help="Path to a custom .codesage.yaml config file.")
@click.pass_context
def web_console_command(ctx, config_path: Optional[str]) -> None:
    """Launch the CodeSage web console."""
    audit_logger = ctx.obj.audit_logger
    try:
        loaded_config = load_config(config_path)
        web_config_dict = loaded_config.get("web", {})
        web_config = WebConsoleConfig.model_validate(web_config_dict)

        app = create_app(web_config)

        click.echo(f"Starting CodeSage web console on http://{web_config.host}:{web_config.port}")
        uvicorn.run(app, host=web_config.host, port=web_config.port)
    finally:
        audit_logger.log(
            AuditEvent(
                timestamp=datetime.now(),
                event_type="cli.web_console",
                project_name=None,
                command="web-console",
                args={"config_path": config_path},
            )
        )
