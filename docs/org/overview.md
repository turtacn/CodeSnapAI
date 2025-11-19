# Organization Governance Hub

## Goal

The Organization Governance Hub in CodeSage is designed to provide a high-level view of the health and governance status across multiple projects. It aggregates data from individual project analyses to help teams prioritize their efforts and identify cross-project trends.

## Architecture

The hub operates on a read-only basis, aggregating existing artifacts from individual projects. It **does not** modify project code or interact with CI/CD pipelines directly.

The core components are:

- **OrgConfig**: A configuration file that defines the projects to be included in the organization view.
- **OrgAggregator**: A component that reads the `ProjectSnapshot`, `ReportProjectSummary`, `TrendSeries`, and `GovernancePlan` artifacts from each project.
- **Health Scoring**: A weighted formula to calculate a health score for each project.
- **Org Report**: A JSON or Markdown report that summarizes the organization's health.
- **Web Console View**: A dashboard in the web console that visualizes the organization's health.

## Boundaries

- The Organization Governance Hub **only reads** existing artifacts. It does not run analyses on the projects.
- It **does not** replace project-level CI/CD checks or reports. It provides a supplementary, high-level view.
- The `jules` assistant still operates on a single-project, single-task basis. The organization view is used to select which project and task to work on next.
