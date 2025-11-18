from pathlib import Path
import yaml
import pytest
from datetime import datetime, timezone
from codesage.snapshot.models import (
    ProjectSnapshot,
    FileSnapshot,
    FileMetrics,
    SnapshotMetadata,
    DependencyGraph,
)
from codesage.snapshot.yaml_generator import YAMLGenerator

@pytest.fixture
def project_snapshot():
    metadata = SnapshotMetadata(
        version="1.0",
        timestamp=datetime.now(timezone.utc),
        project_name="test-project",
        file_count=2,
        total_size=1024,
        tool_version="0.1.0",
        config_hash="dummy_hash",
    )
    files = [
        FileSnapshot(
            path="my_project/module1/file1.py",
            language="python",
            metrics=FileMetrics(num_classes=1, num_functions=2),
            symbols={},
        ),
        FileSnapshot(
            path="my_project/module2/file2.py",
            language="python",
            metrics=FileMetrics(num_classes=0, num_functions=3),
            symbols={},
        ),
    ]
    dependencies = DependencyGraph(internal=[], external=[])

    return ProjectSnapshot(
        metadata=metadata,
        files=files,
        dependencies=dependencies,
    )

def test_yaml_generator_project_snapshot_shape(project_snapshot, tmp_path):
    generator = YAMLGenerator()
    output_path = tmp_path / "snapshot.yaml"
    generator.export(project_snapshot, output_path)

    with open(output_path, "r") as f:
        data = yaml.safe_load(f)

    assert "metadata" in data
    assert "files" in data
    assert "dependencies" in data

def test_yaml_generator_backward_compat_modules_view(project_snapshot, tmp_path):
    generator = YAMLGenerator()
    output_path = tmp_path / "snapshot.yaml"
    generator.export(project_snapshot, output_path, compat_modules_view=True)

    with open(output_path, "r") as f:
        data = yaml.safe_load(f)

    assert "modules" in data
    assert "my_project.module1" in data["modules"]
    assert "my_project.module2" in data["modules"]
    assert data["modules"]["my_project.module1"]["num_classes"] == 1
    assert data["modules"]["my_project.module2"]["num_functions"] == 3
