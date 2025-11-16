import click
from codesage.snapshot.versioning import SnapshotVersionManager
from codesage.snapshot.markdown_generator import MarkdownGenerator

# This would be loaded from the config file
# For now, we'll use a default config.
DEFAULT_CONFIG = {
    "snapshot": {
        "versioning": {
            "max_versions": 10,
            "retention_days": 30
        }
    }
}
SNAPSHOT_DIR = ".codesage/snapshots"

@click.command()
@click.argument('snapshot_version')
@click.option('--template', '-t', help='The name of the report template to use.')
@click.option('--output', '-o', type=click.Path(), required=True, help='The output path for the report.')
@click.option('--include-code', is_flag=True, help='Include code snippets in the report.')
def report(snapshot_version, template, output, include_code):
    """
    Generate a report from a snapshot.
    """
    manager = SnapshotVersionManager(SNAPSHOT_DIR, DEFAULT_CONFIG['snapshot'])
    snapshot = manager.load_snapshot(snapshot_version)

    if not snapshot:
        click.echo(f"Snapshot {snapshot_version} not found.", err=True)
        return

    generator = MarkdownGenerator()

    # The `export` method takes a template name, but for now we'll just use the default.
    # The `include_code` option would be passed to the generator or template.
    template_name = template if template else "default_report.md.jinja2"

    generator.export(snapshot, output, template_name=template_name)

    click.echo(f"Report for snapshot {snapshot_version} saved to {output}")

if __name__ == '__main__':
    report()
