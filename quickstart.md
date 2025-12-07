# CodeSage Quickstart

This guide provides a brief overview of the `codesage` command-line tool and its most common commands.

## Installation

To install `codesage`, you will need Python 3.10+ and Poetry. Once you have these prerequisites, you can install the tool with the following command:

```bash
poetry install
```

## Usage

All `codesage` commands are run through the `poetry run` command to ensure that the correct environment is used.

### Snapshot

The `snapshot` command is used to create and manage snapshots of your codebase.

#### `snapshot create`

The `snapshot create` command generates a semantic snapshot of your project. This snapshot can be used for a variety of purposes, including code analysis, documentation generation, and more.

```bash
poetry run codesage snapshot create [OPTIONS] <PATH>
```

**Arguments:**

*   `<PATH>`: The path to the project you want to create a snapshot of.

**Options:**

*   `--project <NAME>`: The name of the project. If not provided, the name of the directory will be used.
*   `--format [yaml|json|md]`: The format of the snapshot. The default is `yaml`.
*   `--output <PATH>`: The path to the output file. If not provided, the snapshot will be named `<PROJECT_NAME>_snapshot.<FORMAT>` and saved in the current directory.
*   `--language [python|go|shell|java|auto]`: The language of the project. If `auto` is selected, the tool will attempt to detect the language automatically. The default is `auto`.

**Examples:**

*   Create a YAML snapshot of a Python project:

    ```bash
    poetry run codesage snapshot create --language python --format yaml ./my-python-project
    ```

*   Create a JSON snapshot of a Go project and save it to a specific file:

    ```bash
    poetry run codesage snapshot create --language go --format json --output ./snapshots/my-go-project.json ./my-go-project
    ```
