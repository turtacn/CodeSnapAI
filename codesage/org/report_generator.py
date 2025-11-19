from __future__ import annotations

import json
from typing import Dict

from codesage.org.models import OrgGovernanceOverview
from codesage.org.report_models import OrgProjectRow, OrgReportSummary


def render_org_report_json(overview: OrgGovernanceOverview) -> str:
    """Renders the organization overview into a JSON string."""
    projects_by_risk_level: Dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    for p in overview.projects:
        projects_by_risk_level[p.risk_level] = projects_by_risk_level.get(p.risk_level, 0) + 1

    summary = OrgReportSummary(
        total_projects=overview.total_projects,
        projects_by_language={},  # Placeholder, as language is not in OrgProjectHealth
        projects_by_risk_level=projects_by_risk_level,
        projects_with_regressions=overview.projects_with_regressions,
        projects=[
            OrgProjectRow(
                name=p.project.name,
                risk_level=p.risk_level,
                error_issues=p.error_issues,
                has_recent_regression=p.has_recent_regression,
                open_governance_tasks=p.open_governance_tasks,
                health_score=p.health_score,
            )
            for p in overview.projects
        ],
    )
    return json.dumps(summary.model_dump(), indent=2)


def render_org_report_markdown(overview: OrgGovernanceOverview) -> str:
    """Renders the organization overview into a Markdown string."""
    lines = [
        "# Organization Governance Report",
        "",
        "## Overview",
        "",
        f"- **Total Projects**: {overview.total_projects}",
        f"- **Average Health Score**: {overview.avg_health_score:.2f}",
        f"- **Projects with Recent Regressions**: {overview.projects_with_regressions}",
        "",
        "## Projects Summary",
        "",
        "| Project | Health Score | Risk Level | Error Issues | Open Tasks | Regressions |",
        "|---|---|---|---|---|---|",
    ]

    for p in overview.projects:
        regression_icon = "⚠️" if p.has_recent_regression else "✅"
        lines.append(
            f"| {p.project.name} | {p.health_score:.2f} | {p.risk_level.title()} | "
            f"{p.error_issues} | {p.open_governance_tasks} | {regression_icon} |"
        )

    return "\n".join(lines)
