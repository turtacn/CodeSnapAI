# Policy DSL

The Policy DSL allows you to define rules that are evaluated against project snapshots to automate governance decisions.

## Syntax

Policies are defined in YAML or TOML files. A policy file contains a list of rules. Each rule has a unique ID, a scope, a set of conditions, and a list of actions.

### Rule

- `id`: A unique identifier for the rule.
- `scope`: The scope of the rule. Currently, only `project` is supported.
- `conditions`: A list of conditions that must all be met for the rule to trigger.
- `actions`: A list of actions to take if the conditions are met.

### Condition

- `field`: The field to evaluate. See the list of available fields below.
- `op`: The comparison operator. One of `==`, `!=`, `>`, `<`, `>=`, `<=`, `in`, `not in`.
- `value`: The value to compare against.

### Action

- `type`: The type of action to take.
- `params`: A dictionary of parameters for the action.

### Available Fields for Project Scope

- `project_name`: The name of the project.
- `languages`: A list of languages in the project.
- `risk_level`: The overall risk level of the project (`low`, `medium`, `high`).
- `high_risk_files`: The number of high-risk files.
- `total_issues`: The total number of issues.
- `error_issues`: The number of error-severity issues.
- `high_risk_files_delta`: The change in the number of high-risk files.
- `error_issues_delta`: The change in the number of error-severity issues.
- `has_regression`: A boolean indicating if a regression was detected.

### Action Types

- `raise_warning`: Raise a warning in the CI logs.
- `suggest_block_ci`: Suggest that the CI build should be blocked. The `severity` of the `PolicyDecision` will be set to `error`.
- `prioritize_governance_task`: (Not yet implemented) This action can be used to prioritize tasks in the governance plan.

## Example

```yaml
rules:
  - id: "high_risk_alert"
    scope: "project"
    conditions:
      - field: "high_risk_files"
        op: ">"
        value: 0
    actions:
      - type: "raise_warning"
        params: {category: "risk"}

  - id: "block_on_errors"
    scope: "project"
    conditions:
      - field: "error_issues"
        op: ">"
        value: 5
    actions:
      - type: "suggest_block_ci"

  - id: "python_project_policy"
    scope: "project"
    conditions:
      - field: "languages"
        op: "in"
        value: ["python"]
      - field: "risk_level"
        op: "=="
        value: "high"
    actions:
      - type: "raise_warning"
        params: {category: "risk"}
```
