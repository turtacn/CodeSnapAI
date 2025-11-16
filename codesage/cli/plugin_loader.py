import importlib.util
import inspect
import os
from pathlib import Path
import click

def load_plugins(cli_group, plugins_dir=".codesage/plugins"):
    """
    Dynamically loads plugins from the specified directory.
    """
    plugins_path = Path(plugins_dir)
    if not plugins_path.exists():
        return

    for plugin_file in plugins_path.glob("*.py"):
        try:
            spec = importlib.util.spec_from_file_location(plugin_file.stem, plugin_file)
            plugin_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin_module)

            if hasattr(plugin_module, 'register_command') and callable(plugin_module.register_command):
                plugin_module.register_command(cli_group)
            else:
                click.echo(f"Warning: Plugin {plugin_file.name} does not have a 'register_command' function.", err=True)
        except Exception as e:
            click.echo(f"Warning: Could not load plugin {plugin_file.name}: {e}", err=True)

if __name__ == '__main__':
    @click.group()
    def cli():
        pass

    # To test, create a dummy plugin file in .codesage/plugins
    # e.g., .codesage/plugins/my_plugin.py
    # import click
    # def register_command(cli_group):
    #     @cli_group.command()
    #     def hello():
    #         click.echo("Hello from plugin!")

    os.makedirs(".codesage/plugins", exist_ok=True)
    with open(".codesage/plugins/my_plugin.py", "w") as f:
        f.write("import click\n")
        f.write("def register_command(cli_group):\n")
        f.write("    @cli_group.command()\n")
        f.write("    def hello():\n")
        f.write("        click.echo('Hello from plugin!')\n")

    load_plugins(cli)
    cli()
