from datetime import datetime
import pytest
from codesage.report.generator import ReportGenerator
from codesage.snapshot.models import ProjectSnapshot, FileSnapshot, SnapshotMetadata, FileMetrics

@pytest.fixture
def multilang_snapshot():
    metadata = SnapshotMetadata(
        version="1.0",
        timestamp=datetime.now(),
        project_name="multilang-project",
        file_count=3,
        total_size=1024,
        tool_version="0.1.0",
        config_hash="dummy_hash",
    )
    files = [
        FileSnapshot(path="test.py", language="python", metrics=FileMetrics(lines_of_code=10)),
        FileSnapshot(path="main.go", language="go", metrics=FileMetrics(lines_of_code=20)),
        FileSnapshot(path="script.sh", language="shell", metrics=FileMetrics(lines_of_code=30)),
    ]
    return ProjectSnapshot(metadata=metadata, files=files)

def test_multilang_report_extension(multilang_snapshot):
    project_summary, file_summaries = ReportGenerator.from_snapshot(multilang_snapshot)

    assert set(project_summary.languages) == {"python", "go", "shell"}
    assert project_summary.files_per_language["python"] == 1
    assert project_summary.files_per_language["go"] == 1
    assert project_summary.files_per_language["shell"] == 1

    assert len(file_summaries) == 3
    assert file_summaries[0].language == "python"
    assert file_summaries[1].language == "go"
    assert file_summaries[2].language == "shell"
