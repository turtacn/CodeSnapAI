from __future__ import annotations
from typing import List, Optional

from codesage.governance.task_models import GovernancePlan, GovernanceTask

RISK_LEVEL_MAP = {"low": 1, "medium": 2, "high": 3, "unknown": 0}

class TaskOrchestrator:
    def __init__(self, plan: GovernancePlan) -> None:
        self._plan = plan
        self._all_tasks: List[GovernanceTask] = self._flatten_tasks()

    def _flatten_tasks(self) -> List[GovernanceTask]:
        """Extracts and flattens all tasks from the plan's groups."""
        tasks = []
        for group in self._plan.groups:
            tasks.extend(group.tasks)
        return tasks

    def _risk_meet(self, task_risk_level: str, min_risk_level: str) -> bool:
        """Checks if a task's risk level meets the minimum requirement."""
        task_level = RISK_LEVEL_MAP.get(task_risk_level, 0)
        min_level = RISK_LEVEL_MAP.get(min_risk_level, 0)
        return task_level >= min_level

    def select_tasks(
        self,
        *,
        language: Optional[str] = None,
        rule_ids: Optional[List[str]] = None,
        min_risk_level: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[GovernanceTask]:
        """
        Selects and filters tasks based on the given criteria.
        """
        filtered_tasks = self._all_tasks

        if language:
            filtered_tasks = [t for t in filtered_tasks if t.language == language]

        if rule_ids:
            filtered_tasks = [t for t in filtered_tasks if t.rule_id in rule_ids]

        if min_risk_level:
            filtered_tasks = [
                t for t in filtered_tasks if self._risk_meet(t.risk_level, min_risk_level)
            ]

        # Sort by priority (lower is better)
        filtered_tasks.sort(key=lambda x: x.priority)

        if limit is not None:
            return filtered_tasks[:limit]

        return filtered_tasks
