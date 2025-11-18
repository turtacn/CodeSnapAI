from typing import List
from codesage.rules.base import BaseRule, RuleContext
from codesage.snapshot.models import Issue, IssueLocation
from codesage.config.rules_python_baseline import RulesPythonBaselineConfig

class RuleHighCyclomaticFunction(BaseRule):
    rule_id = "PY_HIGH_CYCLOMATIC_FUNCTION"
    description = "Checks for functions with cyclomatic complexity exceeding a threshold."
    default_severity = "warning"

    def check(self, ctx: RuleContext) -> List[Issue]:
        issues = []
        threshold = ctx.config.max_cyclomatic_threshold
        # Assuming function details are stored in symbols
        functions = ctx.file.symbols.get("functions_detail", []) if ctx.file.symbols else []

        for func in functions:
            if func.get("cyclomatic_complexity", 0) > threshold:
                loc = IssueLocation(
                    file_path=ctx.file.path,
                    line=func.get("start_line", 1),
                )
                issue = Issue(
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    message=f"Function '{func.get('name')}' has a cyclomatic complexity of {func.get('cyclomatic_complexity')}, which exceeds the threshold of {threshold}.",
                    location=loc,
                    symbol=func.get("name"),
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
                rule_id=self.rule_id,
                severity=self.default_severity,
                message=f"File has {metrics.lines_of_code} lines of code, which exceeds the threshold of {threshold}.",
                location=loc,
                tags=["size"],
            )
            issues.append(issue)
        return issues


class RuleMissingTypeHintsInPublicAPI(BaseRule):
    rule_id = "PY_MISSING_TYPE_HINTS"
    description = "Checks for missing type hints in public API functions."
    default_severity = "info"

    def check(self, ctx: RuleContext) -> List[Issue]:
        issues = []
        functions = ctx.file.symbols.get("functions_detail", []) if ctx.file.symbols else []

        for func in functions:
            func_name = func.get("name", "")
            # A simple definition of public API: not starting with an underscore.
            if not func_name.startswith("_"):
                params = func.get("params", [])
                has_return_type = func.get("return_type") is not None

                # Check for untyped params. This is a simplification.
                # A real implementation would check the `params` list for types.
                if not has_return_type: # Simplified check
                    loc = IssueLocation(
                        file_path=ctx.file.path,
                        line=func.get("start_line", 1),
                    )
                    issue = Issue(
                        rule_id=self.rule_id,
                        severity=self.default_severity,
                        message=f"Public function '{func_name}' is missing a return type hint.",
                        location=loc,
                        symbol=func_name,
                        tags=["typing", "readability"],
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
    if config.enable_missing_type_hints_rule:
        rules.append(RuleMissingTypeHintsInPublicAPI())
    return rules
