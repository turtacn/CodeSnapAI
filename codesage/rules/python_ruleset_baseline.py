from typing import List
from codesage.rules.base import BaseRule, RuleContext
from codesage.snapshot.models import Issue, IssueLocation
from codesage.config.rules_python_baseline import RulesPythonBaselineConfig
import uuid

class RuleHighCyclomaticFunction(BaseRule):
    rule_id = "PY_HIGH_CYCLOMATIC_FUNCTION"
    description = "Checks for functions with cyclomatic complexity exceeding a threshold."
    default_severity = "warning"

    def check(self, ctx: RuleContext) -> List[Issue]:
        issues = []
        threshold = ctx.config.max_cyclomatic_threshold
        metrics = ctx.file.metrics

        # This is a simplification. A real implementation would need function-level complexity from symbols.
        if metrics and metrics.max_cyclomatic_complexity > threshold:
            loc = IssueLocation(
                file_path=ctx.file.path,
                line=1, # Placeholder: we don't have the exact line number of the function
            )
            issue = Issue(
                id=str(uuid.uuid4()),
                rule_id=self.rule_id,
                severity=self.default_severity,
                message=f"File contains at least one function with cyclomatic complexity of {metrics.max_cyclomatic_complexity}, which exceeds the threshold of {threshold}.",
                location=loc,
                tags=["complexity", "hotspot"],
            )
            issues.append(issue)
        return issues

class RuleHighFanOutFile(BaseRule):
    rule_id = "PY_HIGH_FAN_OUT"
    description = "Checks for files with high fan-out."
    default_severity = "warning"

    def check(self, ctx: RuleContext) -> List[Issue]:
        issues = []
        threshold = ctx.config.fan_out_threshold
        metrics = ctx.file.metrics

        if metrics and metrics.fan_out > threshold:
            loc = IssueLocation(file_path=ctx.file.path, line=1)
            issue = Issue(
                id=str(uuid.uuid4()),
                rule_id=self.rule_id,
                severity=self.default_severity,
                message=f"File has a fan-out of {metrics.fan_out}, which exceeds the threshold of {threshold}.",
                location=loc,
                tags=["coupling"],
            )
            issues.append(issue)
        return issues


class RuleLargeFile(BaseRule):
    rule_id = "PY_LARGE_FILE"
    description = "Checks for files with a large number of lines of code."
    default_severity = "info"

    def check(self, ctx: RuleContext) -> List[Issue]:
        issues = []
        threshold = ctx.config.loc_threshold
        metrics = ctx.file.metrics

        if metrics and metrics.lines_of_code > threshold:
            loc = IssueLocation(file_path=ctx.file.path, line=1)
            issue = Issue(
                id=str(uuid.uuid4()),
                rule_id=self.rule_id,
                severity=self.default_severity,
                message=f"File has {metrics.lines_of_code} lines of code, which exceeds the threshold of {threshold}.",
                location=loc,
                tags=["size"],
            )
            issues.append(issue)
        return issues

def get_python_baseline_rules(config: RulesPythonBaselineConfig) -> List[BaseRule]:
    rules: List[BaseRule] = []
    if config.enable_high_cyclomatic_rule:
        rules.append(RuleHighCyclomaticFunction())
    if config.enable_high_fan_out_rule:
        rules.append(RuleHighFanOutFile())
    if config.enable_large_file_rule:
        rules.append(RuleLargeFile())
    return rules
