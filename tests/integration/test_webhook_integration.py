from pathlib import Path
from click.testing import CliRunner
import json
from pytest_httpserver import HTTPServer
from datetime import datetime, UTC
import yaml

from codesage.cli.main import main
from codesage.snapshot.models import ProjectSnapshot, SnapshotMetadata, FileSnapshot

def create_test_snapshot(tmp_path: Path, project_name: str) -> Path:
    snapshot = ProjectSnapshot(
        metadata=SnapshotMetadata(
            version="1.0",
            timestamp=datetime.now(UTC),
            project_name=project_name,
            file_count=0,
            total_size=0,
            tool_version="0.1.0",
            config_hash="abc",
        ),
        files=[],
        languages=[],
    )
    snapshot_path = tmp_path / f"{project_name}_snapshot.yaml"
    with snapshot_path.open("w") as f:
        yaml.dump(snapshot.model_dump(mode="json"), f)
    return snapshot_path

def test_webhook_success(tmp_path: Path, httpserver: HTTPServer):
    """Test that a successful webhook call does not affect the command outcome."""
    runner = CliRunner()
    httpserver.expect_request("/", method="POST").respond_with_json({"status": "ok"})

    (tmp_path / ".codesage.yaml").write_text(f"""
audit:
  log_dir: "{tmp_path}/audit"
integrations:
  webhook:
    url: "{httpserver.url_for('/')}"
    enabled: true
""")

    snapshot_path = create_test_snapshot(tmp_path, "test-project")

    result = runner.invoke(
        main,
        ["--config", str(tmp_path / ".codesage.yaml"), "report", "--input", str(snapshot_path)],
    )

    assert result.exit_code == 0
    httpserver.check_assertions()

def test_webhook_network_failure(tmp_path: Path):
    """Test that a network failure in the webhook does not affect the command outcome."""
    runner = CliRunner()

    (tmp_path / ".codesage.yaml").write_text(f"""
audit:
  log_dir: "{tmp_path}/audit"
integrations:
  webhook:
    url: "http://localhost:12345" # A port that is unlikely to be in use
    enabled: true
""")

    snapshot_path = create_test_snapshot(tmp_path, "test-project")

    result = runner.invoke(
        main,
        ["--config", str(tmp_path / ".codesage.yaml"), "report", "--input", str(snapshot_path)],
    )

    assert result.exit_code == 0

def test_webhook_server_error(tmp_path: Path, httpserver: HTTPServer):
    """Test that a server error in the webhook does not affect the command outcome."""
    runner = CliRunner()
    httpserver.expect_request("/", method="POST").respond_with_data(status=500)

    (tmp_path / ".codesage.yaml").write_text(f"""
audit:
  log_dir: "{tmp_path}/audit"
integrations:
  webhook:
    url: "{httpserver.url_for('/')}"
    enabled: true
""")

    snapshot_path = create_test_snapshot(tmp_path, "test-project")

    result = runner.invoke(
        main,
        ["--config", str(tmp_path / ".codesage.yaml"), "report", "--input", str(snapshot_path)],
    )

    assert result.exit_code == 0
    httpserver.check_assertions()
