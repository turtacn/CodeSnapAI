import pytest
from codesage.rules.python_ruleset_baseline import (
    RuleHighCyclomaticFunction,
    RuleHighFanOutFile,
    RuleLargeFile,
    RuleMissingTypeHintsInPublicAPI,
)
from codesage.snapshot.models import (
    FileSnapshot,
    FileMetrics,
    ProjectSnapshot,
    SnapshotMetadata,
)
from datetime import datetime
from codesage.config.rules_python_baseline import RulesPythonBaselineConfig
from codesage.rules.base import RuleContext


@pytest.fixture
def baseline_config():
    return RulesPythonBaselineConfig.default()


@pytest.fixture
def minimal_metadata():
    """Provides a minimal valid SnapshotMetadata."""
    return SnapshotMetadata(
        version="1.0",
        timestamp=datetime.now(),
        project_name="test",
        file_count=1,
        total_size=0,
        tool_version="0.1.0",
        config_hash="dummy",
    )


def test_high_cyclomatic_rule_triggers_issue(baseline_config, minimal_metadata):
    rule = RuleHighCyclomaticFunction()
    baseline_config.max_cyclomatic_threshold = 5
    file_snapshot = FileSnapshot(
        path="test.py",
        language="python",
        symbols={
            "functions_detail": [
                {
                    "name": "complex_func",
                    "cyclomatic_complexity": 10,
                    "start_line": 5,
                }
            ]
        },
    )
    project_snapshot = ProjectSnapshot(metadata=minimal_metadata, files=[file_snapshot])
    ctx = RuleContext(
        project=project_snapshot, file=file_snapshot, config=baseline_config
    )
    issues = rule.check(ctx)
    assert len(issues) == 1
    assert issues[0].rule_id == "PY_HIGH_CYCLOMATIC_FUNCTION"
    assert issues[0].location.line == 5


def test_high_fan_out_rule_triggers_issue(baseline_config, minimal_metadata):
    rule = RuleHighFanOutFile()
    baseline_config.fan_out_threshold = 5
    file_snapshot = FileSnapshot(
        path="test.py",
        language="python",
        metrics=FileMetrics(fan_out=10),
    )
    project_snapshot = ProjectSnapshot(metadata=minimal_metadata, files=[file_snapshot])
    ctx = RuleContext(
        project=project_snapshot, file=file_snapshot, config=baseline_config
    )
    issues = rule.check(ctx)
    assert len(issues) == 1
    assert issues[0].rule_id == "PY_HIGH_FAN_OUT"


def test_large_file_rule_not_triggered_when_loc_under_threshold(
    baseline_config, minimal_metadata
):
    rule = RuleLargeFile()
    baseline_config.loc_threshold = 100
    file_snapshot = FileSnapshot(
        path="test.py",
        language="python",
        metrics=FileMetrics(lines_of_code=50),
    )
    project_snapshot = ProjectSnapshot(metadata=minimal_metadata, files=[file_snapshot])
    ctx = RuleContext(
        project=project_snapshot, file=file_snapshot, config=baseline_config
    )
    issues = rule.check(ctx)
    assert len(issues) == 0


def test_missing_type_hints_rule_generates_issue_for_public_api(
    baseline_config, minimal_metadata
):
    rule = RuleMissingTypeHintsInPublicAPI()
    file_snapshot = FileSnapshot(
        path="test.py",
        language="python",
        symbols={
            "functions_detail": [
                {
                    "name": "public_func",
                    "return_type": None,
                    "start_line": 10,
                }
            ]
        },
    )
    project_snapshot = ProjectSnapshot(metadata=minimal_metadata, files=[file_snapshot])
    ctx = RuleContext(
        project=project_snapshot, file=file_snapshot, config=baseline_config
    )
    issues = rule.check(ctx)
    assert len(issues) == 1
    assert issues[0].rule_id == "PY_MISSING_TYPE_HINTS"
    assert issues[0].location.line == 10
