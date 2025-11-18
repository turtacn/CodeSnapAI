import pytest
from codesage.config.rules_python_baseline import RulesPythonBaselineConfig
from codesage.rules.base import RuleContext
from codesage.rules.python_ruleset_baseline import (
    RuleHighCyclomaticFunction,
    RuleHighFanOutFile,
    RuleLargeFile,
)
from codesage.snapshot.models import ProjectSnapshot, FileSnapshot, FileMetrics, SnapshotMetadata
from datetime import datetime

@pytest.fixture
def base_context():
    metadata = SnapshotMetadata(
        version="1.0",
        timestamp=datetime.now(),
        project_name="test",
        file_count=1,
        total_size=1,
        tool_version="1.0",
        config_hash="abc",
    )
    project = ProjectSnapshot(metadata=metadata, files=[])
    file = FileSnapshot(path="test.py", language="python", metrics=FileMetrics())
    project.files.append(file)
    config = RulesPythonBaselineConfig.default()
    return RuleContext(project=project, file=file, config=config)

def test_high_cyclomatic_rule_triggers_issue(base_context):
    base_context.file.metrics.max_cyclomatic_complexity = 15
    rule = RuleHighCyclomaticFunction()
    issues = rule.check(base_context)
    assert len(issues) == 1
    assert issues[0].rule_id == "PY_HIGH_CYCLOMATIC_FUNCTION"

def test_high_fan_out_rule_triggers_issue(base_context):
    base_context.file.metrics.fan_out = 20
    rule = RuleHighFanOutFile()
    issues = rule.check(base_context)
    assert len(issues) == 1
    assert issues[0].rule_id == "PY_HIGH_FAN_OUT"

def test_large_file_rule_not_triggered(base_context):
    base_context.file.metrics.lines_of_code = 100
    rule = RuleLargeFile()
    issues = rule.check(base_context)
    assert len(issues) == 0
