import click
import os
import yaml

from codesage.cli.interactive import run_wizard

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'templates', 'default_config.yaml')
USER_CONFIG_PATH = '.codesage.yaml'

@click.group()
def config():
    """Manage the CodeSage configuration."""
    pass

@config.command('init')
@click.option('--interactive', '-i', is_flag=True, help='Run the interactive configuration wizard.')
@click.option('--force', is_flag=True, help='Overwrite an existing configuration file.')
def init(interactive, force):
    """Initialize a new configuration file."""
    if os.path.exists(USER_CONFIG_PATH) and not force:
        click.echo(f"Configuration file already exists at {USER_CONFIG_PATH}", err=True)
        click.echo("Use --force to overwrite.")
        return

    if interactive:
        config_data = run_wizard()
        if config_data:
            with open(USER_CONFIG_PATH, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False)
    else:
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
        config_data = yaml.safe_load(f) or {}

    keys = key.split('.')
    d = config_data
    for k in keys[:-1]:
        d = d.setdefault(k, {})

    try:
        value = yaml.safe_load(value)
    except yaml.YAMLError:
        pass

    d[keys[-1]] = value

    with open(USER_CONFIG_PATH, 'w') as f:
        yaml.dump(config_data, f, default_flow_style=False)

    click.echo(f"Set {key} to {value}")
