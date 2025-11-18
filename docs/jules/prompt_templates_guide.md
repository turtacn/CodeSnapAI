# Jules Prompt Templates Guide

This document explains the purpose and usage of each prompt template for interacting with Jules.

## High Complexity Refactor (`high_complexity_refactor`)

*   **Purpose**: To refactor functions with high cyclomatic complexity.
*   **Applicable Rules**: `PY_HIGH_CYCLOMATIC_FUNCTION`
*   **Usage**: Copy the generated prompt into Jules to get a refactored version of the function.

## Add Type Hints (`add_type_hints_public_api`)

*   **Purpose**: To add missing type hints to public APIs.
*   **Applicable Rules**: `PY_MISSING_TYPE_HINTS`
*   **Usage**: Use the generated prompt to have Jules add the appropriate type annotations.

## Shell Script Hardening (`shell_script_hardening`)

*   **Purpose**: To improve the security and robustness of shell scripts.
*   **Applicable Rules**: `SH_INSECURE_SCRIPT`
*   **Usage**: This prompt will guide Jules to add `set -euo pipefail` and other best practices.

## Go Refactor Basic (`go_refactor_basic`)

*   **Purpose**: For basic refactoring of Go code.
*   **Applicable Rules**: General Go rules.
*   **Usage**: A general-purpose prompt for simple Go refactoring tasks.
