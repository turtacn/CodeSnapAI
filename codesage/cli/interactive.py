import questionary
import yaml
import click

USER_CONFIG_PATH = '.codesage.yaml'

def run_wizard():
    """Runs an interactive wizard to generate a .codesage.yaml configuration file."""

    click.echo("Welcome to the CodeSage configuration wizard!")

    languages = questionary.checkbox(
        "Select the languages you want to analyze:",
        choices=['python', 'go', 'javascript', 'typescript', 'java']
    ).ask()

    exclude = questionary.text(
        "Enter file patterns to exclude (comma-separated):",
        default=".*,node_modules,vendor"
    ).ask()

    snapshot_formats = questionary.checkbox(
        "Select the snapshot formats to generate:",
        choices=['json', 'markdown', 'yaml'],
        default=['json', 'markdown']
    ).ask()

    complexity_threshold = questionary.text(
        "Set the high complexity threshold:",
        default="10",
        validate=lambda x: x.isdigit()
    ).ask()

    compress_snapshots = questionary.confirm(
        "Enable snapshot compression?",
        default=True
    ).ask()

    max_versions = questionary.text(
        "Maximum number of snapshots to keep:",
        default="10",
        validate=lambda x: x.isdigit()
    ).ask()

    retention_days = questionary.text(
        "Number of days to keep snapshots:",
        default="30",
        validate=lambda x: x.isdigit()
    ).ask()

    config = {
        "analysis": {
            "languages": languages,
            "exclude": [e.strip() for e in exclude.split(',')],
            "complexity_thresholds": {
                "high": int(complexity_threshold)
            }
        },
        "snapshot": {
            "formats": snapshot_formats,
            "compression": {
                "enabled": compress_snapshots
            },
            "versioning": {
                "max_versions": int(max_versions),
                "retention_days": int(retention_days)
            }
        }
    }

    click.echo("\nGenerated configuration:")
    click.echo(yaml.dump(config))

    confirm = questionary.confirm("Save this configuration?").ask()

    if confirm:
        with open(USER_CONFIG_PATH, 'w') as f:
            yaml.dump(config, f)
        click.echo(f"Configuration saved to {USER_CONFIG_PATH}")

    return config

if __name__ == '__main__':
    run_wizard()
