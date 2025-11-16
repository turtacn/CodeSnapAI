import pytest
from pathlib import Path
from codesage.snapshot.json_generator import JSONGenerator
from codesage.snapshot.markdown_generator import MarkdownGenerator
from codesage.snapshot.compressor import SnapshotCompressor
from codesage.snapshot.versioning import SnapshotVersionManager
from codesage.snapshot.differ import SnapshotDiffer
from codesage.snapshot.models import ProjectSnapshot

@pytest.fixture
def snapshot_v1():
    """Loads a sample snapshot from a fixture."""
    path = Path("tests/fixtures/snapshot_samples/full_snapshot_v1.json")
    return ProjectSnapshot.model_validate_json(path.read_text())

@pytest.fixture
def snapshot_v2():
    """Loads a second sample snapshot for comparison."""
    path = Path("tests/fixtures/snapshot_samples/incremental_snapshot.json")
    snapshot = ProjectSnapshot.model_validate_json(path.read_text())
    snapshot.metadata.version = "v2"
    return snapshot

def test_full_pipeline(snapshot_v1, snapshot_v2, tmp_path):
    """
    Tests a complete end-to-end workflow:
    1. Save two versions of a snapshot.
    2. Load them back.
    3. Generate a diff.
    4. Verify the generated Markdown report.
    """
    # 1. Versioning
    config = {
        "versioning": {"max_versions": 5, "retention_days": 30},
        "compression": {"exclude_patterns": []}
    }
    version_manager = SnapshotVersionManager(str(tmp_path), config)

    version_manager.save_snapshot(snapshot_v1)
    version_manager.save_snapshot(snapshot_v2)

    # 2. Loading
    loaded_v1 = version_manager.load_snapshot("v1")
    loaded_v2 = version_manager.load_snapshot("v2")
    assert loaded_v1 and loaded_v2
    assert loaded_v1.metadata.version == "v1"
    assert loaded_v2.metadata.version == "v2"

    # 3. Diffing
    differ = SnapshotDiffer()
    diff = differ.diff(loaded_v1, loaded_v2)
    assert "src/utils.py" in diff.added_files
    assert "src/main.py" in [f.path for f in diff.modified_files]

    # 4. Markdown Generation
    md_generator = MarkdownGenerator(template_dir="codesage/snapshot/templates")
    md_path = tmp_path / "report.md"
    md_generator.export(snapshot_v2, str(md_path))
    assert md_path.exists()

    md_content = md_path.read_text()
    assert "Project Overview" in md_content
    assert "Total Files           | 2" in md_content # From snapshot_v2 data
