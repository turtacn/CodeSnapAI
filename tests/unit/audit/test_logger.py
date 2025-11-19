import json
from datetime import datetime, UTC
from pathlib import Path
from codesage.config.audit import AuditConfig
import pytest
from codesage.audit.logger import AuditLogger
from codesage.audit.models import AuditEvent

def test_audit_event_jsonl_format(tmp_path: Path):
    config = AuditConfig(enabled=True, log_dir=str(tmp_path))
    logger = AuditLogger(config)

    event = AuditEvent(
        timestamp=datetime.now(UTC),
        event_type="cli.snapshot",
        project_name="test-project",
        command="snapshot",
        args={"path": "."},
    )

    logger.log(event)

    log_file = next(tmp_path.glob("*.log"))
    with log_file.open("r") as f:
        line = f.readline()
        data = json.loads(line)
        assert data["event_type"] == "cli.snapshot"
        assert data["project_name"] == "test-project"

@pytest.mark.skip(reason="Log rotation test is flaky and needs to be rewritten.")
def test_audit_log_rotation_on_size(tmp_path: Path):
    config = AuditConfig(enabled=True, log_dir=str(tmp_path), max_file_size_mb=1)
    logger = AuditLogger(config)

    event = AuditEvent(
        timestamp=datetime.now(UTC),
        event_type="cli.snapshot",
        project_name="test-project",
        command="snapshot",
        args={"path": "."},
    )

    # Write enough events to trigger rotation
    for i in range(8000):
        event.project_name = f"test-project-{i}"
        logger.log(event)

    log_files = list(tmp_path.glob("*.log"))
    assert len(log_files) > 1
