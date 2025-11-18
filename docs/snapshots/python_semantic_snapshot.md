# Python Semantic Snapshot

This document describes the structure and fields of the Python semantic snapshot, a YAML-based representation of a Python project's structure and metrics.

## YAML Structure

The snapshot is organized into three main sections: `metadata`, `files`, and `dependencies`.

- **metadata**: Contains information about the snapshot itself, such as the version, timestamp, and project name.
- **files**: A list of snapshots for each file in the project, including metrics and symbols.
- **dependencies**: A graph of the project's internal and external dependencies.

## Field Mapping

The fields in the YAML file map to the `ProjectSnapshot` Pydantic model in `codesage/snapshot/models.py`.

| YAML Field      | Pydantic Model      | Description                               |
|-----------------|---------------------|-------------------------------------------|
| `metadata`      | `SnapshotMetadata`  | Metadata for the snapshot.                |
| `files`         | `List[FileSnapshot]` | A list of snapshots for each file.        |
| `dependencies`  | `DependencyGraph`   | The project's dependency graph.           |

### FileSnapshot Fields

| YAML Field | Pydantic Model | Description                                      |
|------------|----------------|--------------------------------------------------|
| `path`     | `str`          | The relative path to the file.                   |
| `language` | `str`          | The programming language of the file.            |
| `metrics`  | `FileMetrics`  | A summary of the file's metrics.                 |
| `symbols`  | `Dict[str, Any]`| A dictionary of symbols defined in the file.     |

### FileMetrics Fields

| YAML Field        | Pydantic Model | Description                                      |
|-------------------|----------------|--------------------------------------------------|
| `num_classes`     | `int`          | The number of classes in the file.               |
| `num_functions`   | `int`          | The number of functions in the file.             |
| `num_methods`     | `int`          | The number of methods in the file.               |
| `has_async`       | `bool`         | Whether the file contains async code.            |
| `uses_type_hints` | `bool`         | Whether the file uses type hints.                |

## Example Output

```yaml
metadata:
  version: '1.0'
  timestamp: '2023-10-27T10:00:00.000000'
  project_name: 'my-project'
  file_count: 1
  total_size: 123
  tool_version: '0.1.0'
  config_hash: 'dummy_hash'
files:
- path: 'my_project/main.py'
  language: 'python'
  metrics:
    num_classes: 1
    num_functions: 1
    num_methods: 2
    has_async: true
    uses_type_hints: true
  symbols:
    classes:
    - 'MyClass'
    functions:
    - 'my_function'
dependencies:
  internal: []
  external: []
```

## Complexity and Risk Fields

### FileMetrics

The `FileMetrics` model has been extended to include the following complexity and coupling metrics:

- `lines_of_code`: The total number of lines in the file.
- `max_cyclomatic_complexity`: The highest cyclomatic complexity of any function in the file.
- `avg_cyclomatic_complexity`: The average cyclomatic complexity of all functions in the file.
- `high_complexity_functions`: The number of functions with a cyclomatic complexity greater than the configured threshold.
- `fan_in`: The number of other files that import the current file.
- `fan_out`: The number of other files that are imported by the current file.

### FileRisk

The `FileRisk` model provides a risk assessment for each file.

- `risk_score`: A normalized score between 0 and 1, where 1 is the highest risk.
- `level`: The risk level, which can be "low", "medium", or "high".
- `factors`: A list of strings that identify the factors contributing to the risk score.

### ProjectRiskSummary

The `ProjectRiskSummary` model provides a summary of the risk for the entire project.

- `avg_risk`: The average risk score across all files.
- `high_risk_files`: The number of files with a high risk level.
- `medium_risk_files`: The number of files with a medium risk level.
- `low_risk_files`: The number of files with a low risk level.

### Example YAML

```yaml
files:
  - path: my_module/my_file.py
    language: python
    metrics:
      lines_of_code: 100
      max_cyclomatic_complexity: 12
      avg_cyclomatic_complexity: 4.5
      high_complexity_functions: 1
      fan_in: 5
      fan_out: 2
    risk:
      risk_score: 0.75
      level: high
      factors:
        - high_cyclomatic_complexity
risk_summary:
  avg_risk: 0.35
  high_risk_files: 1
  medium_risk_files: 5
  low_risk_files: 10
```

### Issues View

The snapshot now includes an `issues` view, which provides a list of potential problems identified by the rule engine.

- **`FileSnapshot.issues`**: A list of `Issue` objects found in the file. Each `Issue` object contains detailed information about the rule that was triggered, the location of the issue, and a descriptive message.
- **`ProjectSnapshot.issues_summary`**: A summary of all issues found in the project, including the total number of issues, a breakdown by severity, and a breakdown by rule.

It is important to note that the `issues` are generated independently of the `risk` score. While a file with many issues is likely to have a high risk score, the two systems provide different perspectives on code quality. The risk score is a high-level heuristic, while the issues view provides specific, actionable feedback.

### LLM-Assisted Remediation Suggestions

The `Issue` model can be further enriched with LLM-assisted remediation suggestions. This is an optional step that can be performed by running the `llm-suggest` CLI command.

When this step is performed, the following fields are added to each `Issue` object:

- `llm_fix_hint`: A brief, actionable suggestion for fixing the issue.
- `llm_rationale`: A brief explanation of why the suggested fix is recommended.
- `llm_status`: The status of the LLM suggestion.
- `llm_model`: The name of the LLM model used to generate the suggestion.
- `llm_last_updated_at`: The timestamp when the suggestion was last updated.
