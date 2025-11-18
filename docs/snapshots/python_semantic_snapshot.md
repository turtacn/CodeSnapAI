# Python Semantic Snapshot

The Python semantic snapshot provides a deep analysis of Python code, including detailed metrics, risk assessment, and issue detection. It is one of the language implementations within the multi-language snapshot framework.

## Integration with the Unified Model

The Python snapshot builder populates the unified snapshot models with Python-specific data.

### `FileSnapshot`

- `language`: Set to `"python"`.

### `FileMetrics`

The `language_specific` field of the `FileMetrics` model is populated with the following Python-specific metrics:

- `num_classes`: The number of classes in the file.
- `num_methods`: The number of methods in the file.
- `has_async`: Whether the file contains `async` code.
- `uses_type_hints`: Whether the file uses type hints.
- `max_cyclomatic_complexity`: The maximum cyclomatic complexity of any function in the file.
- `avg_cyclomatic_complexity`: The average cyclomatic complexity of functions in the file.
- `high_complexity_functions`: The number of functions with high cyclomatic complexity.
- `fan_in`: The number of files that depend on this file.
- `fan_out`: The number of files this file depends on.
