import click
from pathlib import Path
import yaml
from codesage.snapshot.models import ProjectSnapshot
from codesage.llm.client import DummyLLMClient
from codesage.llm.issue_suggester import IssueSuggester
from codesage.config.llm import LLMConfig
from codesage.snapshot.yaml_generator import YAMLGenerator


@click.command('llm-suggest')
@click.option('--input', '-i', 'input_path', type=click.Path(exists=True, dir_okay=False), required=True, help='Input snapshot YAML file.')
@click.option('--output', '-o', 'output_path', type=click.Path(), required=True, help='Output snapshot YAML file.')
@click.option('--provider', type=click.Choice(['dummy']), default='dummy', help='LLM provider to use.')
@click.option('--model', type=str, default='dummy-model', help='LLM model to use.')
def llm_suggest(input_path, output_path, provider, model):
    """Enrich a snapshot with LLM-powered suggestions."""

    with open(input_path, 'r') as f:
        snapshot_data = yaml.safe_load(f)

    project_snapshot = ProjectSnapshot.model_validate(snapshot_data)

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
