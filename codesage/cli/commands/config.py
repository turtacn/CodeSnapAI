import click
import os
import yaml

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'templates', 'default_config.yaml')
USER_CONFIG_PATH = '.codesage.yaml'

@click.group()
def config():
    """Manage the CodeSage configuration."""
    pass

from codesage.cli.interactive import run_wizard

@config.command('init')
def init():
    """Initialize a new configuration file."""
    if os.path.exists(USER_CONFIG_PATH):
        overwrite = click.confirm(
            f"Configuration file already exists at {USER_CONFIG_PATH}. Overwrite?",
            default=False
        )
        if not overwrite:
            click.echo("Initialization cancelled.")
            return

    with open(DEFAULT_CONFIG_PATH, 'r') as f:
        default_config = f.read()

    with open(USER_CONFIG_PATH, 'w') as f:
        f.write(default_config)

    click.echo(f"Configuration file created at {USER_CONFIG_PATH}")

@config.command('validate')
def validate():
    """Validate the configuration file."""
    if not os.path.exists(USER_CONFIG_PATH):
        click.echo(f"Configuration file not found at {USER_CONFIG_PATH}", err=True)
        return

    try:
        with open(USER_CONFIG_PATH, 'r') as f:
            yaml.safe_load(f)
        click.echo("Configuration file is valid.")
    except yaml.YAMLError as e:
        click.echo(f"Configuration file is invalid:\n{e}", err=True)

@config.command('show')
def show():
    """Show the current configuration."""
    if not os.path.exists(USER_CONFIG_PATH):
        click.echo(f"Configuration file not found at {USER_CONFIG_PATH}", err=True)
        return

    with open(USER_CONFIG_PATH, 'r') as f:
        click.echo(f.read())

@config.command('set')
@click.argument('key')
@click.argument('value')
def set_value(key, value):
    """Set a configuration value."""
    if not os.path.exists(USER_CONFIG_PATH):
        click.echo(f"Configuration file not found at {USER_CONFIG_PATH}", err=True)
        return

    with open(USER_CONFIG_PATH, 'r') as f:
        config_data = yaml.safe_load(f)

    keys = key.split('.')
    d = config_data
    for k in keys[:-1]:
        d = d.get(k, {})

    # Attempt to convert value to a more appropriate type
    if value.lower() == 'true':
        value = True
    elif value.lower() == 'false':
        value = False
    elif value.isdigit():
        value = int(value)

    d[keys[-1]] = value

    with open(USER_CONFIG_PATH, 'w') as f:
        yaml.dump(config_data, f)

    click.echo(f"Set {key} to {value}")

if __name__ == '__main__':
    config()
