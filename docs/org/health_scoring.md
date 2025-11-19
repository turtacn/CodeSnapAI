# Project Health Scoring

The project health score is a metric designed to provide a quick overview of a project's quality and governance status. It is calculated based on a weighted formula that considers several factors.

## Formula

The health score is calculated as follows:

```
health_score = max(0.0, 100.0 -
  (risk_weight * high_risk_files) -
  (issues_weight * error_issues) -
  (regression_weight * has_recent_regression) +
  (governance_progress_weight * completion_ratio)
)
```

- `high_risk_files`: The number of files with a 'high' or 'critical' risk level.
- `error_issues`: The number of issues with 'error' severity.
- `has_recent_regression`: A boolean flag (1 or 0) that indicates if a regression was detected in the latest analysis.
- `completion_ratio`: The ratio of completed governance tasks to the total number of tasks (0.0 to 1.0).

## Configuration

The weights for each factor can be configured in the `.codesage.yaml` file under the `org.health_weights` key.

Example:

```yaml
org:
  health_weights:
    risk_weight: 2.0
    issues_weight: 0.1
    regression_weight: 15.0
    governance_progress_weight: 10.0
```

## Interpretation

The health score ranges from 0 to 100, where higher is better.

- **80-100**: The project is in good shape, with few high-risk files or critical issues.
- **60-80**: The project has some technical debt that should be addressed.
- **Below 60**: The project requires immediate attention.
