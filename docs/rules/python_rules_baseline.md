# Python Baseline Ruleset

This document outlines the baseline ruleset for Python projects in codesage. These rules are designed to identify common issues related to code complexity, style, and potential bugs.

## Rule Engine

The rule engine is a core component of codesage that analyzes the project snapshot and applies a set of configurable rules to identify issues. The engine iterates over each file in the snapshot and executes the enabled rules, generating a list of issues for each file.

The rule engine is configured in the `.codesage.yaml` file under the `rules.python_baseline` section.

## Baseline Rules

The following rules are included in the baseline ruleset:

### `PY_HIGH_CYCLOMATIC_FUNCTION`

- **Description:** Checks for functions with cyclomatic complexity exceeding a threshold.
- **Default Severity:** `warning`
- **Tags:** `complexity`, `hotspot`
- **Configuration:** `max_cyclomatic_threshold` (default: 10)

### `PY_HIGH_FAN_OUT`

- **Description:** Checks for files with high fan-out.
- **Default Severity:** `warning`
- **Tags:** `coupling`
- **Configuration:** `fan_out_threshold` (default: 15)

### `PY_LARGE_FILE`

- **Description:** Checks for files with a large number of lines of code.
- **Default Severity:** `info`
- **Tags:** `size`
- **Configuration:** `loc_threshold` (default: 500)

### `PY_MISSING_TYPE_HINTS`

- **Description:** Checks for missing type hints in public API functions.
- **Default Severity:** `info`
- **Tags:** `typing`, `readability`
- **Configuration:** `enable_missing_type_hints_rule` (default: `False`)

## YAML Example

The following is an example of the `issues` and `issues_summary` fields in the YAML output:

```yaml
issues_summary:
  total_issues: 2
  by_severity:
    warning: 1
    info: 1
  by_rule:
    PY_HIGH_CYCLOMATIC_FUNCTION: 1
    PY_LARGE_FILE: 1
files:
  - path: my_module/my_file.py
    # ... other file data
    issues:
      - id: PY_HIGH_CYCLOMATIC_FUNCTION:my_module/my_file.py:42
        rule_id: PY_HIGH_CYCLOMATIC_FUNCTION
        severity: warning
        message: "Function 'my_complex_function' has a cyclomatic complexity of 12, which exceeds the threshold of 10."
        location:
          file_path: my_module/my_file.py
          line: 42
        symbol: my_complex_function
        tags:
          - complexity
          - hotspot
```
