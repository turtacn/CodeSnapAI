"""Git 历史数据挖掘器
实现架构设计第 3.1.3 节的"代码演化分析"能力
"""
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Set
import os

try:
    from git import Repo, InvalidGitRepositoryError
except ImportError:
    Repo = None
    InvalidGitRepositoryError = None

logger = logging.getLogger(__name__)

class GitMiner:
    """Git 历史挖掘器

    核心指标（对齐架构设计）:
    - 变更频率: 近 N 天内的提交次数
    - 文件热度: 累计变更行数 / 文件总行数 (这里简化为变更次数，后续可扩展)
    - 作者分散度: 不同作者数量（高分散度 = 高风险）
    """

    def __init__(self, repo_path: Optional[str] = None):
        self.repo_path = repo_path or os.getcwd()
        self.repo = None
        self._churn_cache: Dict[str, int] = {}
        self._author_cache: Dict[str, Set[str]] = {}
        self._cache_initialized = False

        if Repo:
            try:
                self.repo = Repo(self.repo_path, search_parent_directories=True)
            except (InvalidGitRepositoryError, Exception) as e:
                logger.warning(f"Failed to initialize Git repo at {self.repo_path}: {e}")

    def _initialize_stats(self, days: int = 90):
        """Bulk process commits to populate caches."""
        if self._cache_initialized:
            return

        if not self.repo:
            return

        try:
            since_date = datetime.now() - timedelta(days=days)
            # Use traverse_commits for potentially faster iteration if supported, otherwise standard iteration
            # Iterating over all commits once is O(N_commits * M_files_changed) which is better than O(F_files * N_commits)
            commits = self.repo.iter_commits(since=since_date)

            for commit in commits:
                # stats.files returns dict {path: stats}
                for file_path in commit.stats.files.keys():
                    self._churn_cache[file_path] = self._churn_cache.get(file_path, 0) + 1

                    if file_path not in self._author_cache:
                        self._author_cache[file_path] = set()
                    self._author_cache[file_path].add(commit.author.email)

            self._cache_initialized = True
        except Exception as e:
            logger.error(f"Error initializing git stats: {e}")

    def get_file_churn_score(self, file_path: str, days: int = 90) -> float:
        """计算文件变更频率评分（0-10）

        算法: score = min(10, commit_count / (days / 30))
        - 月均 1 次提交 = 1 分
        - 月均 10 次提交 = 10 分（满分）
        """
        if not self.repo:
            return 0.0

        # Ensure cache is populated
        self._initialize_stats(days)

        # We need exact path match.
        # Note: git paths are relative to repo root. `file_path` usually is relative too.
        # But we might need normalization if `file_path` comes from different source.
        # Assuming consistency for now.

        commit_count = self._churn_cache.get(file_path, 0)

        denominator = max(days / 30, 1) # avoid division by zero
        score = min(10.0, commit_count / denominator)
        return round(score, 2)

    def get_file_author_count(self, file_path: str) -> int:
        """统计文件的历史贡献者数量

        用于评估"维护一致性风险":
        - 1 人维护: 低风险（知识集中）
        - 5+ 人维护: 高风险（理解成本高）
        """
        if not self.repo:
            return 0

        self._initialize_stats()

        authors = self._author_cache.get(file_path, set())
        return len(authors)

    def get_hotspot_files(self, top_n: int = 20) -> List[Dict]:
        """识别代码热点（高频变更文件）
        """
        if not self.repo:
            return []

        self._initialize_stats()

        sorted_files = sorted(self._churn_cache.items(), key=lambda x: x[1], reverse=True)[:top_n]

        result = []
        for path, count in sorted_files:
            result.append({
                "path": path,
                "commits": count
            })
        return result
