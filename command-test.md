# CodeSage Command Test Plan

This document outlines the commands to be tested to ensure the new project-aware snapshot functionality is working correctly and that other commands have not been affected.

## Test Setup

1. Create two dummy project directories in `tests/fixtures`: `project-a` and `project-b`.
2. Each project should contain a few dummy source files (e.g., `main.py`, `utils.py`).
3. Create a dummy governance plan file `plan.yml` and a dummy task file `task.yml`.

## Snapshot Command Tests (`codesage snapshot`)

### Project A

1.  **Create first snapshot for Project A:**
    ```bash
    poetry run codesage snapshot create ./project-a
    ```

2.  **Create second snapshot for Project A:**
    ```bash
    # (after making some changes to a file in project-a)
    poetry run codesage snapshot create ./project-a
    ```

3.  **List snapshots for Project A:**
    ```bash
    poetry run codesage snapshot list --project project-a
    ```
    *Expected output: Should list v1 and v2.*

4.  **Show snapshot v1 for Project A:**
    ```bash
    poetry run codesage snapshot show v1 --project project-a
    ```

### Project B

1.  **Create first snapshot for Project B:**
    ```bash
    poetry run codesage snapshot create ./project-b
    ```

2.  **List snapshots for Project B:**
    ```bash
    poetry run codesage snapshot list --project project-b
    ```
    *Expected output: Should list only v1.*

3.  **List snapshots for Project A again:**
    ```bash
    poetry run codesage snapshot list --project project-a
    ```
    *Expected output: Should still list v1 and v2, unaffected by Project B.*

### Cleanup

1.  **Cleanup snapshots for Project A (dry run):**
    ```bash
    poetry run codesage snapshot cleanup --project project-a --dry-run
    ```

2.  **Cleanup snapshots for Project A:**
    ```bash
    poetry run codesage snapshot cleanup --project project-a
    ```

8.  **Create a snapshot with an overridden project name:**
    ```bash
    poetry run codesage snapshot create ./project-a --project project-c
    ```

9.  **List snapshots for the overridden project name:**
    ```bash
    poetry run codesage snapshot list --project project-c
    ```
    *Expected output: Should list v1.*


## Diff Command Tests (`codesage diff`)

1.  **Compare two snapshots within Project A:**
    ```bash
    poetry run codesage diff v1 v2 --project project-a
    ```

## Other Commands (Regression Testing)

These commands were not expected to be changed, but we should run them to ensure they still work.

1.  **Analyze:**
    ```bash
    poetry run codesage analyze tests/fixtures/project-a
    ```

2.  **Config:**
    ```bash
    poetry run codesage config show
    ```

3.  **Scan:**
    ```bash
    poetry run codesage scan tests/fixtures/project-a
    ```

## New Commands Tests

1.  **Governance Plan:**
    ```bash
    poetry run codesage governance-plan --snapshot-version v1 --project project-a --output plan.yml
    ```

2.  **LLM Suggest:**
    ```bash
    poetry run codesage llm-suggest --snapshot-version v1 --project project-a --output enriched_snapshot.yml
    ```

3.  **Jules Prompt (with plan):**
    ```bash
    poetry run codesage jules-prompt --plan plan.yml --task-id <task_id> --project project-a --snapshot-version v1
    ```

4.  **Jules Prompt (with task):**
    ```bash
    poetry run codesage jules-prompt --task task.yml --project project-a --snapshot-version v1
    ```
