import pytest
from datetime import datetime
from codesage.config.rules_python_baseline import RulesPythonBaselineConfig
from codesage.rules.base import BaseRule, RuleContext
from codesage.rules.engine import RuleEngine
from codesage.snapshot.models import ProjectSnapshot, FileSnapshot, Issue, IssueLocation, SnapshotMetadata

class DummyRule(BaseRule):
    rule_id = "DUMMY_RULE"
    description = "A dummy rule for testing."

    def check(self, ctx: RuleContext) -> list[Issue]:
        return [Issue(
            id=f"{self.rule_id}:{ctx.file.path}:1",
            rule_id=self.rule_id,
            severity="info",
            message="Dummy issue",
            location=IssueLocation(file_path=ctx.file.path, line=1),
        )]

def test_rule_engine_applies_all_rules_to_all_files():
    metadata = SnapshotMetadata(
        version="1.0",
        timestamp=datetime.now(),
        project_name="test",
        file_count=2,
        total_size=2,
        tool_version="1.0",
        config_hash="abc",
    )
    files = [
        FileSnapshot(path="file1.py", language="python"),
        FileSnapshot(path="file2.py", language="python"),
    ]
    project = ProjectSnapshot(metadata=metadata, files=files)

    rules = [DummyRule(), DummyRule()] # Two rules
    engine = RuleEngine(rules=rules)

    result_project = engine.run(project, RulesPythonBaselineConfig.default())

    assert len(result_project.files[0].issues) == 2
    assert len(result_project.files[1].issues) == 2
    assert result_project.issues_summary.total_issues == 4
    assert result_project.issues_summary.by_rule["DUMMY_RULE"] == 4
