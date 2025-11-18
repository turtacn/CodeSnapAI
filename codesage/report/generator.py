from __future__ import annotations
from typing import Tuple, List, Dict
from codesage.snapshot.models import ProjectSnapshot
from codesage.report.summary_models import ReportProjectSummary, ReportFileSummary


class ReportGenerator:
    @staticmethod
    def from_snapshot(snapshot: ProjectSnapshot) -> Tuple[ReportProjectSummary, List[ReportFileSummary]]:
        file_summaries: List[ReportFileSummary] = []

        total_files = len(snapshot.files)
        high_risk_files = medium_risk_files = low_risk_files = 0
        total_issues = error_issues = warning_issues = info_issues = 0
        rule_count: Dict[str, int] = {}
        risky_files: List[Tuple[str, float]] = []

        files_per_language: Dict[str, int] = {}

        for file in snapshot.files:
            lang = getattr(file, "language", "unknown")
            files_per_language[lang] = files_per_language.get(lang, 0) + 1
            risk_level = getattr(file.risk, "level", "low") if file.risk else "low"
            risk_score = getattr(file.risk, "risk_score", 0.0) if file.risk else 0.0
            loc = getattr(file.metrics, "lines_of_code", 0) if file.metrics else 0
            num_functions = getattr(file.metrics, "num_functions", 0) if file.metrics else 0

            f_issues_total = len(file.issues)
            f_error = sum(1 for i in file.issues if i.severity == "error")
            f_warning = sum(1 for i in file.issues if i.severity == "warning")

            total_issues += f_issues_total
            error_issues += f_error
            warning_issues += f_warning
            info_issues += sum(1 for i in file.issues if i.severity == "info")

            if risk_level == "high":
                high_risk_files += 1
            elif risk_level == "medium":
                medium_risk_files += 1
            else:
                low_risk_files += 1

            for issue in file.issues:
                rule_count[issue.rule_id] = rule_count.get(issue.rule_id, 0) + 1

            risky_files.append((file.path, risk_score))

            file_rule_count: Dict[str, int] = {}
            for issue in file.issues:
                file_rule_count[issue.rule_id] = file_rule_count.get(issue.rule_id, 0) + 1
            top_issue_rules = sorted(file_rule_count.keys(), key=lambda r: file_rule_count[r], reverse=True)

            file_summary = ReportFileSummary(
                path=file.path,
                language=lang,
                risk_level=risk_level,
                risk_score=risk_score,
                loc=loc,
                num_functions=num_functions,
                issues_total=f_issues_total,
                issues_error=f_error,
                issues_warning=f_warning,
                top_issue_rules=top_issue_rules[:3],
            )
            file_summaries.append(file_summary)

        top_rules = sorted(rule_count.keys(), key=lambda r: rule_count[r], reverse=True)
        risky_files_sorted = sorted(risky_files, key=lambda t: t[1], reverse=True)
        top_risky_files = [p for p, _ in risky_files_sorted[:10]]

        languages = list(files_per_language.keys())

        project_summary = ReportProjectSummary(
            total_files=total_files,
            high_risk_files=high_risk_files,
            medium_risk_files=medium_risk_files,
            low_risk_files=low_risk_files,
            total_issues=total_issues,
            error_issues=error_issues,
            warning_issues=warning_issues,
            info_issues=info_issues,
            top_rules=top_rules[:10],
            top_risky_files=top_risky_files,
            languages=languages,
            files_per_language=files_per_language,
        )

        return project_summary, file_summaries
