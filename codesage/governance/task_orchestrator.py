from __future__ import annotations
from typing import List, Optional
from pathlib import Path

import structlog
from codesage.governance.task_models import GovernancePlan, GovernanceTask
from codesage.llm.client import BaseLLMClient, LLMRequest
from codesage.governance.patch_manager import PatchManager

logger = structlog.get_logger()

RISK_LEVEL_MAP = {"low": 1, "medium": 2, "high": 3, "unknown": 0}

class TaskOrchestrator:
    def __init__(self, plan: GovernancePlan, llm_client: Optional[BaseLLMClient] = None) -> None:
        self._plan = plan
        self._all_tasks: List[GovernanceTask] = self._flatten_tasks()
        self.llm_client = llm_client
        self.patch_manager = PatchManager()

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

    def execute_task(self, task: GovernanceTask, apply_fix: bool = False) -> bool:
        """
        Executes a governance task using the LLM client and optionally applies the fix.
        """
        if not self.llm_client:
            logger.warning("LLM client not configured, skipping execution", task_id=task.id)
            return False

        logger.info("Executing task", task_id=task.id, file=task.file_path)

        # 1. Prepare context and prompt
        # Assuming task.context contains necessary info or we read file
        file_path = Path(task.file_path)
        if not file_path.exists():
            logger.error("File not found", file_path=str(file_path))
            return False

        file_content = file_path.read_text(encoding="utf-8")

        # Construct a prompt (This logic might be moved to a PromptBuilder later)
        prompt = (
            f"Fix the following issue in {task.file_path}:\n"
            f"Issue: {task.issue_type} - {task.message}\n"
            f"Severity: {task.severity}\n\n"
            f"Here is the file content:\n"
            f"```\n{file_content}\n```\n\n"
            f"Please provide the FULL corrected file content in a markdown code block."
        )

        # 2. Call LLM
        request = LLMRequest(
            prompt=prompt,
            metadata={"task_id": task.id, "file_path": task.file_path}
        )

        try:
            response = self.llm_client.generate(request)
        except Exception as e:
            logger.error("LLM generation failed", error=str(e))
            return False

        # 3. Extract Code
        new_content = self.patch_manager.extract_code_block(response.content)
        if not new_content:
            logger.error("Failed to extract code from LLM response")
            return False

        # 4. Apply Fix if requested
        if apply_fix:
            success = self.patch_manager.apply_patch(file_path, new_content)
            if success:
                task.status = "done"
                logger.info("Task completed and patch applied", task_id=task.id)
                return True
            else:
                logger.error("Failed to apply patch", task_id=task.id)
                return False
        else:
            # Just generate diff for dry-run
            diff = self.patch_manager.create_diff(file_content, new_content, filename=task.file_path)
            print(f"--- Patch for {task.file_path} ---\n{diff}\n-----------------------------")
            logger.info("Dry run completed", task_id=task.id)
            return True
