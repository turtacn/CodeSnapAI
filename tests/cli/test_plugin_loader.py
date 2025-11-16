from click.testing import CliRunner
from codesage.cli.main import main
from codesage.cli.plugin_loader import load_plugins
import os
import click

def test_plugin_loader(tmp_path):
    """Test the plugin loader."""
    runner = CliRunner()

    plugins_dir = tmp_path / ".codesage" / "plugins"
    os.makedirs(plugins_dir)

    plugin_code = """
import click

def register_command(cli_group):
    @cli_group.command()
    def helloworld():
        click.echo("Hello from the plugin!")
"""
    (plugins_dir / "my_plugin.py").write_text(plugin_code)

    @click.group()
    def test_cli():
        pass

    load_plugins(test_cli, plugins_dir=str(plugins_dir))

    result = runner.invoke(test_cli, ['helloworld'])

    assert result.exit_code == 0
    assert "Hello from the plugin!" in result.output
