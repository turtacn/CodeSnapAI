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
