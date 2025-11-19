from __future__ import annotations
from typing import Any, List, Optional, Dict

from pydantic import BaseModel, Field

from codesage.snapshot.models import ProjectSnapshot
from codesage.report.summary_models import ReportProjectSummary
from codesage.history.diff_models import ProjectDiffSummary
from codesage.history.regression_detector import RegressionWarning
from .dsl_models import PolicySet, PolicyAction, PolicyDecision


def _match_condition(value: Any, op: str, expected: Any) -> bool:
    if op == "==":
        return value == expected
    if op == "!=":
        return value != expected
    if op == ">":
        return value > expected
    if op == "<":
        return value < expected
    if op == ">=":
        return value >= expected
    if op == "<=":
        return value <= expected
    if op == "in":
        return value in expected
    if op == "not in":
        return value not in expected
    return False


def evaluate_project_policies(
    policy: PolicySet,
    snapshot: ProjectSnapshot,
    report: "ReportProjectSummary",
    diff: Optional[ProjectDiffSummary],
    regressions: Optional[List[RegressionWarning]],
) -> List[PolicyDecision]:
    decisions: List[PolicyDecision] = []

    context: Dict[str, Any] = {
        "project_name": snapshot.metadata.project_name,
        "languages": snapshot.languages,
        "high_risk_files": report.high_risk_files,
        "total_issues": report.total_issues,
        "error_issues": report.error_issues,
        "high_risk_files_delta": diff.high_risk_files_delta if diff else 0,
        "error_issues_delta": diff.error_issues_delta if diff else 0,
        "has_regression": bool(regressions),
    }

    for rule in policy.rules:
        if rule.scope != "project":
            continue

        all_conditions_met = True
        for cond in rule.conditions:
            actual_value = context.get(cond.field)
            if actual_value is None:
                all_conditions_met = False
                break
            if not _match_condition(actual_value, cond.op, cond.value):
                all_conditions_met = False
                break

        if all_conditions_met:
            severity = "warning"
            if any(action.type == "suggest_block_ci" for action in rule.actions):
                severity = "error"

            decision = PolicyDecision(
                rule_id=rule.id,
                scope=rule.scope,
                target=snapshot.metadata.project_name,
                severity=severity,
                actions=rule.actions,
                reason=f"Rule '{rule.id}' matched for project '{snapshot.metadata.project_name}'.",
            )
            decisions.append(decision)

    return decisions
