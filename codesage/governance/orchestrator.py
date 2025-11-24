"""治理任务编排引擎
实现架构设计第 3.2.1 节的完整编排能力
"""
import asyncio
import logging
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import networkx as nx  # 用于依赖图管理
from queue import PriorityQueue

from codesage.history.models import Issue
from codesage.governance.patch_manager import Patch, PatchManager

# Configure logging
logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"
    PENDING_REGENERATION = "pending_regeneration"

class FailureReason(Enum):
    TRANSIENT = "transient"
    CONTEXTUAL = "contextual"
    VALIDATION = "validation"
    CONFLICT = "conflict"
    UNKNOWN = "unknown"

@dataclass
class FixTask:
    """修复任务（增强版）"""
    id: str
    issue: Issue
    patch: Patch
    priority: float  # 基于风险评分计算
    dependencies: List[str] = field(default_factory=list)  # 依赖的任务 ID
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    validation_config: Dict = field(default_factory=dict)

    @property
    def file_path(self) -> str:
        return self.issue.file_path

    def __lt__(self, other):
        # High priority (higher value) comes first.
        return self.priority > other.priority


class FailureAnalyzer:
    """失败原因分析器"""

    def analyze_failure(self, task: FixTask, error: str) -> FailureReason:
        """分析任务失败原因

        分类:
        - TRANSIENT: 临时性错误（网络超时、资源占用）→ 可重试
        - CONTEXTUAL: 上下文不匹配（锚点未找到）→ 需 Jules 重新生成
        - VALIDATION: 验证失败（测试不通过）→ 需人工介入
        - CONFLICT: 代码冲突（Git merge 失败）→ 需人工解决
        """
        error_lower = error.lower()
        if "timeout" in error_lower or "network" in error_lower:
            return FailureReason.TRANSIENT
        elif "anchor not found" in error_lower or "fuzzy match failed" in error_lower:
            return FailureReason.CONTEXTUAL
        elif "test failed" in error_lower or "validation failed" in error_lower:
            return FailureReason.VALIDATION
        elif "merge conflict" in error_lower:
            return FailureReason.CONFLICT
        else:
            return FailureReason.UNKNOWN

class GovernanceOrchestrator:
    """治理任务编排器

    核心能力（对齐架构设计）:
    1. 依赖关系解析（DAG 构建）
    2. 优先级队列调度
    3. 失败重试策略
    4. 并行执行支持
    """

    def __init__(
        self,
        patch_manager: PatchManager,
        max_parallel: int = 3,
        retry_strategy: str = "exponential_backoff",
        failure_analyzer: Optional[FailureAnalyzer] = None
    ):
        self.patch_manager = patch_manager
        self.max_parallel = max_parallel
        self.retry_strategy = retry_strategy
        self.failure_analyzer = failure_analyzer or FailureAnalyzer()

        # 任务依赖图（使用 NetworkX）
        self.task_graph = nx.DiGraph()

        # 优先级队列
        self.task_queue = PriorityQueue()

        # 任务状态跟踪
        self.tasks: Dict[str, FixTask] = {}

    def add_task(self, task: FixTask):
        """添加任务到编排器

        自动分析依赖关系（基于文件依赖）
        """
        self.tasks[task.id] = task
        self.task_graph.add_node(task.id, task=task)

        # 添加依赖边
        for dep_id in task.dependencies:
            self.task_graph.add_edge(dep_id, task.id)

        # 检查循环依赖
        if not nx.is_directed_acyclic_graph(self.task_graph):
            self.task_graph.remove_node(task.id)
            del self.tasks[task.id]
            raise ValueError(f"Circular dependency detected involving task {task.id}")

    def build_execution_plan(self) -> List[List[str]]:
        """构建执行计划（拓扑排序 + 并行分层）

        Returns:
            [
                ["task1", "task2"],  # 第一批（可并行）
                ["task3"],           # 第二批（依赖 task1/task2）
                ["task4", "task5"]   # 第三批
            ]
        """
        # 拓扑排序 (Check if graph is empty first)
        if self.task_graph.number_of_nodes() == 0:
            return []

        if not nx.is_directed_acyclic_graph(self.task_graph):
             raise ValueError("Cannot create execution plan: graph has cycles")

        # 按层级分组（支持并行执行）
        execution_plan = []

        # Copy graph to destructively process it (or just track in-degrees)
        remaining = set(self.tasks.keys())

        while remaining:
            # 找出当前可执行的任务（无未完成的依赖）
            ready = [
                tid for tid in remaining
                if all(
                    dep not in remaining
                    for dep in self.task_graph.predecessors(tid)
                )
            ]

            if not ready:
                raise ValueError("Deadlock detected in task dependencies")

            ready.sort(key=lambda tid: self.tasks[tid])

            execution_plan.append(ready)
            remaining -= set(ready)

        return execution_plan

    async def execute(self) -> Dict[str, TaskStatus]:
        """执行所有任务（异步并行）

        Returns:
            任务 ID → 最终状态的映射
        """
        execution_plan = self.build_execution_plan()
        results = {}

        for batch in execution_plan:
            # 并行执行当前批次（限制并发数）
            batch_results = await self._execute_batch(batch)
            results.update(batch_results)

            # 检查失败任务
            failed = [tid for tid, status in batch_results.items() if status == TaskStatus.FAILED]
            if failed:
                # 跳过依赖失败任务的后续任务
                self._skip_dependent_tasks(failed)

        return results

    async def _execute_batch(self, task_ids: List[str]) -> Dict[str, TaskStatus]:
        """并行执行一批任务"""

        # 限制并发数
        semaphore = asyncio.Semaphore(self.max_parallel)

        async def execute_with_limit(tid):
            async with semaphore:
                if self.tasks[tid].status == TaskStatus.SKIPPED:
                    return tid, TaskStatus.SKIPPED
                return tid, await self._execute_single_task(tid)

        # 并发执行
        if not task_ids:
            return {}

        results_list = await asyncio.gather(*[
            execute_with_limit(tid) for tid in task_ids
        ])

        return dict(results_list)

    async def _execute_single_task(self, task_id: str) -> TaskStatus:
        """执行单个任务（带重试）"""
        task = self.tasks[task_id]
        task.status = TaskStatus.RUNNING

        while task.retry_count <= task.max_retries:
            try:
                # 应用补丁
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(None, self.patch_manager.apply_patch_safe, task)

                if result.success:
                    task.status = TaskStatus.SUCCESS
                    logger.info(f"Task {task.id} succeeded")
                    return TaskStatus.SUCCESS
                else:
                    # 失败 → 分析原因
                    error_msg = result.error or "Unknown error"
                    reason = self.failure_analyzer.analyze_failure(task, error_msg)
                    logger.warning(f"Task {task.id} failed (Attempt {task.retry_count + 1}/{task.max_retries + 1}). Reason: {reason}. Error: {error_msg}")

                    if reason == FailureReason.TRANSIENT:
                         # 临时错误 → 简单重试
                        task.retry_count += 1
                        if task.retry_count <= task.max_retries:
                            task.status = TaskStatus.RETRYING
                            await self._apply_retry_backoff(task)
                        else:
                            task.status = TaskStatus.FAILED
                            return TaskStatus.FAILED

                    elif reason == FailureReason.CONTEXTUAL:
                        # 上下文问题 → 请求 Jules 重新生成
                        logger.warning(f"Task {task_id} needs Jules re-generation")
                        task.status = TaskStatus.PENDING_REGENERATION
                        return TaskStatus.PENDING_REGENERATION

                    elif reason == FailureReason.VALIDATION:
                        # 验证失败 → 人工介入
                        task.status = TaskStatus.FAILED
                        self._create_manual_review_ticket(task, error_msg)
                        return TaskStatus.FAILED

                    elif reason == FailureReason.CONFLICT:
                        # 冲突 -> Fail
                        task.status = TaskStatus.FAILED
                        return TaskStatus.FAILED

                    else:
                        # 其他/未知 -> 重试
                        task.retry_count += 1
                        if task.retry_count <= task.max_retries:
                            task.status = TaskStatus.RETRYING
                            await self._apply_retry_backoff(task)
                        else:
                            task.status = TaskStatus.FAILED
                            return TaskStatus.FAILED

            except Exception as e:
                logger.error(f"Task {task_id} failed with exception: {e}")
                task.retry_count += 1
                if task.retry_count > task.max_retries:
                    task.status = TaskStatus.FAILED
                    return TaskStatus.FAILED
                await self._apply_retry_backoff(task)

        task.status = TaskStatus.FAILED
        return TaskStatus.FAILED

    async def _apply_retry_backoff(self, task: FixTask):
        """应用重试退避策略"""

        if self.retry_strategy == "exponential_backoff":
            delay = 2 ** task.retry_count  # 2s, 4s, 8s
        elif self.retry_strategy == "fixed":
            delay = 5  # 固定 5 秒
        else:
            delay = 1

        logger.info(f"Retrying task {task.id} after {delay}s (attempt {task.retry_count})")
        await asyncio.sleep(delay)

    def _skip_dependent_tasks(self, failed_task_ids: List[str]):
        """跳过依赖失败任务的所有后续任务"""
        for failed_id in failed_task_ids:
            if failed_id not in self.task_graph:
                continue
            # 找出所有依赖该任务的后续任务
            descendants = nx.descendants(self.task_graph, failed_id)
            for desc_id in descendants:
                if self.tasks[desc_id].status == TaskStatus.PENDING:
                    self.tasks[desc_id].status = TaskStatus.SKIPPED
                    logger.warning(f"Skipping task {desc_id} due to failed dependency {failed_id}")

    def _create_manual_review_ticket(self, task: FixTask, error: str):
        """创建人工审查工单（可集成 JIRA/GitHub Issues）"""

        # Issue model has 'description', not 'message'
        issue_desc = getattr(task.issue, 'description', 'No description')
        if not issue_desc:
            # Fallback if description is empty or None
             issue_desc = 'No description'

        ticket = {
            "title": f"CodeSnapAI: Manual review needed for {task.id}",
            "description": f"""
                Task ID: {task.id}
                Issue: {issue_desc}
                Error: {error}
                File: {task.issue.file_path}:{task.issue.line_number}
            """,
            "labels": ["codesnapai", "manual-review", "governance"]
        }
        # TODO: 集成 GitHub Issues API
        logger.info(f"Created manual review ticket: {ticket}")
