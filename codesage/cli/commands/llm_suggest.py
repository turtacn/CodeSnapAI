import click
from pathlib import Path
import yaml
from codesage.snapshot.models import ProjectSnapshot
from codesage.llm.client import DummyLLMClient
from codesage.llm.issue_suggester import IssueSuggester
from codesage.config.llm import LLMConfig
from codesage.snapshot.yaml_generator import YAMLGenerator


from codesage.snapshot.versioning import SnapshotVersionManager
from codesage.config.defaults import SNAPSHOT_DIR, DEFAULT_SNAPSHOT_CONFIG

@click.command('llm-suggest')
@click.option('--snapshot-version', '-s', 'snapshot_version', type=str, required=True, help='The version of the snapshot to use.')
@click.option('--project', '-p', 'project_name', type=str, required=True, help='The name of the project.')
@click.option('--output', '-o', 'output_path', type=click.Path(), required=True, help='Output snapshot YAML file.')
@click.option('--provider', type=click.Choice(['dummy']), default='dummy', help='LLM provider to use.')
@click.option('--model', type=str, default='dummy-model', help='LLM model to use.')
def llm_suggest(snapshot_version, project_name, output_path, provider, model):
    """Enrich a snapshot with LLM-powered suggestions."""

    manager = SnapshotVersionManager(SNAPSHOT_DIR, project_name, DEFAULT_SNAPSHOT_CONFIG['snapshot'])
    project_snapshot = manager.load_snapshot(snapshot_version)
    if not project_snapshot:
        click.echo(f"Snapshot {snapshot_version} not found for project '{project_name}'.", err=True)
        return

    if provider == 'dummy':
        llm_client = DummyLLMClient()
    else:
        # This is where you would add other providers
        raise NotImplementedError(f"Provider '{provider}' is not supported.")

    llm_config = LLMConfig(provider=provider, model=model)

    suggester = IssueSuggester(llm_client, llm_config)
    enriched_snapshot = suggester.enrich_with_llm_suggestions(project_snapshot)

    generator = YAMLGenerator()
    generator.export(enriched_snapshot, Path(output_path))

    click.echo(f"Enriched snapshot saved to {output_path}")
