from __future__ import annotations
import collections
from datetime import datetime
from typing import List, Optional, Dict, Any

from codesage.config.governance import GovernanceConfig
from codesage.governance.task_models import (
    GovernancePlan,
    GovernanceTask,
    GovernanceTaskGroup,
)
from codesage.snapshot.models import ProjectSnapshot, FileSnapshot, Issue, FileRisk


class TaskBuilder:
    def __init__(self, config: GovernanceConfig) -> None:
        self._config = config

    def build_plan(self, snapshot: ProjectSnapshot) -> GovernancePlan:
        tasks: List[GovernanceTask] = []
        project_name = snapshot.metadata.project_name

        for file in snapshot.files:
            file_risk = getattr(file, "risk", None)
            for issue in file.issues:
                task = self._create_task_from_issue(project_name, file, issue, file_risk)
                tasks.append(task)

        tasks = self._apply_limits(tasks)
        groups = self._group_tasks(tasks)
        summary = self._summarize_tasks(tasks)

        plan = GovernancePlan(
            project_name=snapshot.metadata.project_name,
            created_at=datetime.utcnow(),
            summary=summary,
            groups=groups,
        )
        return plan

    def _create_task_from_issue(
        self,
        project_name: str,
        file: FileSnapshot,
        issue: Issue,
        risk: Optional[FileRisk],
    ) -> GovernanceTask:
        priority = self._compute_priority(issue, risk)
        description = (
            f"Fix issue '{issue.rule_id}' in {file.path} at line {issue.location.line}: "
            f"{issue.message}"
        )
        llm_hint = issue.llm_fix_hint or ""
        risk_level = risk.level if risk else "unknown"

        metadata = {
            "line": issue.location.line,
            "symbol": issue.symbol,
            "severity": issue.severity,
            "rule_id": issue.rule_id,
        }

        task = GovernanceTask(
            id=f"{file.path}:{issue.rule_id}:{issue.location.line}",
            project_name=project_name,
            file_path=file.path,
            language=file.language,
            rule_id=issue.rule_id,
            issue_id=issue.id,
            description=description,
            priority=priority,
            risk_level=risk_level,
            llm_hint=llm_hint,
            metadata=metadata,
        )
        return task

    def _compute_priority(self, issue: Issue, risk: Optional[FileRisk]) -> int:
        severity = issue.severity
        risk_level = risk.level if risk else "low"

        if severity == "error":
            if risk_level == "high":
                return 1
            if risk_level == "medium":
                return 2
            return 3
        if severity == "warning":
            if risk_level == "high":
                return 2
            if risk_level == "medium":
                return 3
            return 4
        return 5

    def _apply_limits(self, tasks: List[GovernanceTask]) -> List[GovernanceTask]:
        tasks.sort(key=lambda t: t.priority)

        file_counts = collections.Counter()
        rule_counts = collections.Counter()
        limited_tasks: List[GovernanceTask] = []

        for task in tasks:
            if file_counts[task.file_path] >= self._config.max_tasks_per_file:
                continue
            if rule_counts[task.rule_id] >= self._config.max_tasks_per_rule:
                continue

            limited_tasks.append(task)
            file_counts[task.file_path] += 1
            rule_counts[task.rule_id] += 1

        return limited_tasks

    def _group_tasks(self, tasks: List[GovernanceTask]) -> List[GovernanceTaskGroup]:
        groups: Dict[str, List[GovernanceTask]] = collections.defaultdict(list)
        for t in tasks:
            key = ""
            if self._config.group_by == "rule":
                key = f"rule:{t.rule_id}"
            elif self._config.group_by == "file":
                key = f"file:{t.file_path}"
            elif self._config.group_by == "risk_level":
                key = f"risk:{t.risk_level}"

            if key:
                groups[key].append(t)

        result: List[GovernanceTaskGroup] = []
        for key, items in groups.items():
            # Sort tasks within the group by priority
            items.sort(key=lambda t: t.priority)
            group = GovernanceTaskGroup(
                id=key,
                name=key,
                group_by=self._config.group_by,
                tasks=items,
            )
            result.append(group)

        # Sort groups by the priority of their highest-priority task
        result.sort(key=lambda g: g.tasks[0].priority if g.tasks else 99)
        return result

    def _summarize_tasks(self, tasks: List[GovernanceTask]) -> Dict[str, Any]:
        summary = {
            "total_tasks": len(tasks),
            "by_priority": collections.Counter(t.priority for t in tasks),
            "by_language": collections.Counter(t.language for t in tasks),
            "by_risk_level": collections.Counter(t.risk_level for t in tasks),
        }
        return summary
