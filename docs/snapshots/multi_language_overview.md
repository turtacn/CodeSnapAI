# Multi-Language Snapshot Overview

The snapshot model has been designed to support multiple programming languages in a unified way. This allows for consistent analysis and reporting across different languages in a single project.

## Unified Snapshot Model

The core snapshot models, `ProjectSnapshot` and `FileSnapshot`, are language-agnostic. They provide a common structure for storing information about files, metrics, risks, and issues, regardless of the programming language.

### `ProjectSnapshot`

The `ProjectSnapshot` model includes the following language-related fields:

- `languages`: A list of the languages found in the project (e.g., `["python", "go", "shell"]`).
- `language_stats`: A dictionary containing statistics for each language, such as the number of files.

### `FileSnapshot`

The `FileSnapshot` model includes a `language` field that specifies the programming language of the file (e.g., `"python"`, `"go"`, `"shell"`).

### `FileMetrics`

The `FileMetrics` model has been refactored to separate language-agnostic and language-specific metrics.

- **Language-agnostic metrics:**
    - `lines_of_code`
    - `num_functions`
    - `num_types`
- **Language-specific metrics:**
    - `language_specific`: A dictionary containing metrics that are specific to a particular language. For example, for Python, this might include `num_classes`, `has_async`, etc.

## Supported Languages

Currently, the following languages are supported:

- **Python:** Deep semantic analysis, including cyclomatic complexity, fan-in/fan-out, and type hint detection.
- **Go:** Minimal snapshot, including lines of code, number of functions, number of types, and imports.
- **Shell:** Minimal snapshot, including lines of code, number of functions, and external commands.
