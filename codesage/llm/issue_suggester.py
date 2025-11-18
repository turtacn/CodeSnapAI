from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from codesage.config.llm import LLMConfig
    from codesage.llm.client import LLMClient
    from codesage.snapshot.models import Issue, ProjectSnapshot


from codesage.llm.prompts import build_issue_prompt
from codesage.snapshot.models import LLMCallStats
from codesage.llm.client import LLMRequest


class IssueSuggester:
    def __init__(self, client: "LLMClient", config: "LLMConfig") -> None:
        self._client = client
        self._config = config

    def enrich_with_llm_suggestions(self, project: "ProjectSnapshot") -> "ProjectSnapshot":
        if not self._config.enabled:
            return project

        stats = project.llm_stats or LLMCallStats(total_requests=0, succeeded=0, failed=0)
        total_used = 0

        for file in project.files:
            used_in_file = 0
            for issue in file.issues:
                if not self._should_enrich(issue, used_in_file, total_used):
                    continue

                try:
                    prompt = build_issue_prompt(issue, file, project, self._config)
                    request = LLMRequest(
                        prompt=prompt,
                        model=self._config.model,
                        metadata={
                            "rule_id": issue.rule_id,
                            "severity": issue.severity,
                            "file_path": file.path,
                        },
                    )
                    issue.llm_status = "requested"
                    stats.total_requests += 1
                    response = self._client.generate(request)
                    issue.llm_fix_hint = response.fix_hint
                    issue.llm_rationale = response.rationale
                    issue.llm_model = self._config.model
                    issue.llm_status = "succeeded"
                    issue.llm_last_updated_at = datetime.utcnow()
                    stats.succeeded += 1
                    used_in_file += 1
                    total_used += 1
                except Exception:
                    issue.llm_status = "failed"
                    stats.failed += 1

        project.llm_stats = stats
        return project

    def _should_enrich(self, issue: "Issue", used_in_file: int, total_used: int) -> bool:
        if not self._config.enabled:
            return False
        if issue.llm_status != "not_requested":
            return False
        if issue.severity not in self._config.filter_severity:
            return False
        if used_in_file >= self._config.max_issues_per_file:
            return False
        if total_used >= self._config.max_issues_per_run:
            return False
        return True
