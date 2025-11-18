# Python Baseline Ruleset

This document provides an overview of the baseline rule engine and the set of predefined rules for Python projects.

## Rule Engine

The rule engine is a component of `codesage` that analyzes project snapshots to identify potential issues in the codebase. It operates on a `ProjectSnapshot` object, iterates through each file, and applies a configurable set of rules.

### Data Flow

1.  A `ProjectSnapshot` is created, containing detailed information about each file (metrics, risk, symbols, etc.).
2.  The `RuleEngine` is initialized with a list of active rules.
3.  The engine processes each `FileSnapshot` within the project.
4.  For each file, every active rule's `check` method is called.
5.  The issues identified by the rules are collected and attached to the `FileSnapshot`.
6.  Finally, a project-wide summary of all issues is generated and attached to the `ProjectSnapshot`.

## Baseline Rules

The following rules are included in the baseline ruleset for Python.

### `PY_HIGH_CYCLOMATIC_FUNCTION`

-   **Description**: Identifies functions with a cyclomatic complexity that exceeds a defined threshold. High complexity can indicate that a function is trying to do too much and may be difficult to test and maintain.
-   **Default Severity**: `warning`
-   **Tags**: `complexity`, `hotspot`
-   **Configuration**:
    -   `enable_high_cyclomatic_rule`: Enables or disables this rule.
    -   `max_cyclomatic_threshold`: The complexity value above which an issue is triggered.

### `PY_HIGH_FAN_OUT`

-   **Description**: Identifies files that import a large number of other modules. High fan-out can be a sign of a lack of cohesion and can make the code harder to understand and test.
-   **Default Severity**: `warning`
-   **Tags**: `coupling`
-   **Configuration**:
    -   `enable_high_fan_out_rule`: Enables or disables this rule.
    -   `fan_out_threshold`: The number of imports above which an issue is triggered.

### `PY_LARGE_FILE`

-   **Description**: Identifies files with a large number of lines of code. Large files can be difficult to navigate and understand, and may contain multiple responsibilities.
-   **Default Severity**: `info`
-   **Tags**: `size`
-   **Configuration**:
    -   `enable_large_file_rule`: Enables or disables this rule.
    -   `loc_threshold`: The number of lines above which an issue is triggered.

## Example YAML Output

The issues identified by the rule engine are included in the YAML snapshot output.

```yaml
files:
  - path: 'my_app/core.py'
    # ... other file snapshot data
    issues:
      - id: 'PY_HIGH_CYCLOMATIC_FUNCTION:my_app/core.py:42'
        rule_id: 'PY_HIGH_CYCLOMATIC_FUNCTION'
        severity: 'warning'
        message: 'Function process_data cyclomatic complexity 12 exceeds 10.'
        location:
          file_path: 'my_app/core.py'
          line: 42
        symbol: 'process_data'
        tags: ['complexity', 'hotspot']
        suggested_fix_summary: 'Refactor function into smaller units.'
issues_summary:
  total_issues: 5
  by_severity:
    warning: 3
    info: 2
  by_rule:
    PY_HIGH_CYCLOMATIC_FUNCTION: 1
    PY_HIGH_FAN_OUT: 2
    PY_LARGE_FILE: 2
```
