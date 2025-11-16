import json
import pytest
from jsonschema import validate
import pathlib

from codesage.snapshot.json_generator import JSONGenerator
from codesage.snapshot.models import ProjectSnapshot

# Sample analysis results for testing the generate method
ANALYSIS_RESULTS = [
    {
        "path": "src/main.py",
        "language": "python",
        "hash": "abc",
        "lines": 100,
        "ast_summary": {
            "function_count": 5, "class_count": 1, "import_count": 10, "comment_lines": 15
        },
        "complexity_metrics": {"cyclomatic": 12},
        "detected_patterns": [],
        "issues": [],
    }
]

@pytest.fixture
def project_snapshot():
    """Provides a ProjectSnapshot instance from a fixture file."""
    snapshot_path = pathlib.Path("tests/fixtures/snapshot_samples/full_snapshot_v1.json")
    return ProjectSnapshot.model_validate_json(snapshot_path.read_text())

@pytest.fixture
def json_generator():
    """Provides a JSONGenerator instance."""
    return JSONGenerator()

def test_generate_snapshot(json_generator):
    """Tests that the generate method creates a valid ProjectSnapshot."""
    config = {"some_config": "value"}
    snapshot = json_generator.generate(ANALYSIS_RESULTS, config)

    assert isinstance(snapshot, ProjectSnapshot)
    assert len(snapshot.files) == 1
    assert snapshot.files[0].path == "src/main.py"
    assert snapshot.metadata.tool_version is not None
    assert snapshot.global_metrics["total_files"] == 1

def test_serialize_project_snapshot(json_generator, project_snapshot, tmp_path):
    """Tests that a ProjectSnapshot can be serialized to a JSON file."""
    output_path = tmp_path / "snapshot.json"
    json_generator.export(project_snapshot, str(output_path))
    assert output_path.exists()
    with open(output_path, "r") as f:
        data = json.load(f)
    assert data["metadata"]["version"] == "v1"

def test_validate_json_schema(json_generator, project_snapshot, tmp_path):
    """Tests that the generated JSON conforms to the project schema."""
    schema = json_generator._get_schema()
    snapshot_dict = project_snapshot.model_dump(mode='json')
    validate(instance=snapshot_dict, schema=schema)

def test_compact_mode(json_generator, project_snapshot, tmp_path):
    """Tests the compact (non-pretty) JSON output."""
    output_path = tmp_path / "snapshot_compact.json"
    json_generator.export(project_snapshot, str(output_path), pretty=False)
    content = output_path.read_text()
    assert "\n" not in content
    assert "  " not in content

def test_pretty_print_mode(json_generator, project_snapshot, tmp_path):
    """Tests the pretty-printed JSON output."""
    output_path = tmp_path / "snapshot_pretty.json"
    json_generator.export(project_snapshot, str(output_path), pretty=True)
    content = output_path.read_text()
    assert "\n" in content
    assert '  "metadata":' in content
