from typing import List, Dict
from codesage.rules.base import BaseRule, RuleContext
from codesage.snapshot.models import ProjectSnapshot, ProjectIssuesSummary
from codesage.config.rules_python_baseline import RulesPythonBaselineConfig


class RuleEngine:
    def __init__(self, rules: List[BaseRule]) -> None:
        self._rules = rules

    def run(self, project: ProjectSnapshot, config: RulesPythonBaselineConfig) -> ProjectSnapshot:
        for file in project.files:
            ctx = RuleContext(project=project, file=file, config=config)
            file_issues = []
            for rule in self._rules:
                file_issues.extend(rule.check(ctx))
            file.issues = file_issues

        project.issues_summary = self._summarize_issues(project)
        return project

    def _summarize_issues(self, project: ProjectSnapshot) -> ProjectIssuesSummary:
        total = 0
        by_severity: Dict[str, int] = {}
        by_rule: Dict[str, int] = {}

        for file in project.files:
            for issue in file.issues:
                total += 1
                by_severity[issue.severity] = by_severity.get(issue.severity, 0) + 1
                by_rule[issue.rule_id] = by_rule.get(issue.rule_id, 0) + 1

        return ProjectIssuesSummary(
            total_issues=total,
            by_severity=by_severity,
            by_rule=by_rule,
        )
