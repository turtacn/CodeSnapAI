"""Jules 性能与成本监控器"""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict
import logging
import json

logger = logging.getLogger(__name__)

@dataclass
class JulesMetrics:
    """Jules 调用指标"""
    task_id: str
    issue_type: str
    request_time: datetime
    response_time: datetime
    latency_ms: float
    tokens_used: int
    estimated_cost: float  # 基于 token 价格
    iterations: int
    success: bool
    error_type: Optional[str] = None

class JulesMonitor:
    """Jules 性能监控器（对齐架构设计可观测性要求）"""

    def __init__(self, metrics_db: str = "jules_metrics.db"):
        self.metrics_db = metrics_db
        self.session_metrics: List[JulesMetrics] = []

    def record_call(self, metrics: JulesMetrics):
        """记录单次 Jules 调用指标"""
        self.session_metrics.append(metrics)
        self._persist_to_db(metrics)

    def _persist_to_db(self, metrics: JulesMetrics):
        """Persist metrics to a local file/db (Mock implementation)"""
        # In a real implementation, this would write to SQLite
        pass

    def get_cost_report(self, time_range: str = "today") -> Dict:
        """生成成本报告"""
        total_cost = sum(m.estimated_cost for m in self.session_metrics)
        total_calls = len(self.session_metrics)
        return {
            "total_cost": total_cost,
            "total_calls": total_calls,
            "avg_cost_per_call": total_cost / total_calls if total_calls > 0 else 0.0
        }

    def get_performance_report(self) -> Dict:
        """生成性能报告"""
        latencies = [m.latency_ms for m in self.session_metrics]
        success_count = sum(1 for m in self.session_metrics if m.success)
        total_calls = len(self.session_metrics)

        return {
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
            "success_rate": success_count / total_calls if total_calls > 0 else 0.0,
        }

    def alert_high_cost(self, threshold: float = 50.0):
        """成本告警（超过阈值时发送通知）"""
        current_cost = self.get_cost_report()["total_cost"]
        if current_cost > threshold:
            logger.warning(f"Jules cost exceeded {threshold} USD today! Current: {current_cost}")
