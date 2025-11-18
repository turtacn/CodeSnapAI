import click
import uvicorn
from typing import Optional

from codesage.config.loader import load_config
from codesage.config.web import WebConsoleConfig
from codesage.web.server import create_app

@click.command("web-console")
@click.option("--config", "config_path", help="Path to a custom .codesage.yaml config file.")
def web_console_command(config_path: Optional[str]) -> None:
    """Launch the CodeSage web console."""
    loaded_config = load_config(config_path)
    web_config_dict = loaded_config.get("web", {})
    web_config = WebConsoleConfig.parse_obj(web_config_dict)

    app = create_app(web_config)

    click.echo(f"Starting CodeSage web console on http://{web_config.host}:{web_config.port}")
    uvicorn.run(app, host=web_config.host, port=web_config.port)
