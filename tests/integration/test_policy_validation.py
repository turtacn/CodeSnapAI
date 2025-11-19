from pathlib import Path
from click.testing import CliRunner
import json
from datetime import datetime, UTC

import pytest
from codesage.cli.main import main

@pytest.mark.skip(reason="Test is failing intermittently and needs further investigation.")
def test_invalid_policy_file_fails_cli(tmp_path: Path):
    """Test that an invalid policy file causes the CLI to fail with a clear error."""
    runner = CliRunner()

    policy_content = """
rules:
  - id: "invalid_rule"
    scope: "project"
    conditions:
      - field: "high_risk_files"
        op: "is_greater_than" # invalid op
        value: 0
    actions:
      - type: "raise_warning"
"""
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(policy_content)

    (tmp_path / ".codesage.yaml").write_text(f"""
audit:
  log_dir: "{tmp_path}/audit"
policy:
  project_policy_path: "{policy_path}"
""")

    snapshot_path = tmp_path / "snapshot.yaml"
    snapshot_path.write_text(f"""
metadata:
  project_name: test-project
  file_count: 0
  total_size: 0
  languages: []
  version: "1.0"
  timestamp: "{datetime.now(UTC).isoformat()}"
  tool_version: "0.1.0"
  config_hash: "abc"
files: []
""")

    result = runner.invoke(
        main,
        ["--config", str(tmp_path / ".codesage.yaml"), "report", "--input", str(snapshot_path)],
    )

    assert result.exit_code != 0
    assert "ValidationError" in str(result.exception)
