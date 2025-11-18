# Go and Shell Minimal Snapshots

The Go and Shell snapshots provide a minimal level of analysis, focusing on basic metrics and symbols. These snapshots are designed to be lightweight and provide a foundation for future, more in-depth analysis.

## Go Snapshot

The Go snapshot builder provides the following information:

### `FileSnapshot`

- `language`: Set to `"go"`.

### `FileMetrics`

- `lines_of_code`: The number of lines of code.
- `num_functions`: The number of functions.
- `num_types`: The number of types.

### Symbols

- `imports`: A list of the packages imported by the file.

## Shell Snapshot

The Shell snapshot builder provides the following information:

### `FileSnapshot`

- `language`: Set to `"shell"`.

### `FileMetrics`

- `lines_of_code`: The number of lines of code.
- `num_functions`: The number of functions.
- `language_specific`:
    - `shell`:
        - `external_commands_count`: The number of external commands used in the script.

### Symbols

- `external_commands`: A list of the external commands used in the script.

## Future Extensions

The Go and Shell snapshots can be extended in the future to include more detailed analysis, such as:

- Cyclomatic complexity
- Dependency analysis
- Risk assessment
- Issue detection
