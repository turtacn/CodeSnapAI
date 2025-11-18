# Governance Model

This document describes the data models used in the CodeSage governance feature.

## GovernanceTask

A `GovernanceTask` represents a single, actionable task for improving the codebase.

- `id`: A unique identifier for the task.
- `file_path`: The path to the file that the task is associated with.
- `language`: The programming language of the file.
- `rule_id`: The ID of the rule that was violated.
- `issue_id`: The ID of the issue that the task is associated with.
- `description`: A human-readable description of the task.
- `priority`: The priority of the task.
- `risk_level`: The risk level of the file that the task is associated with.
- `status`: The status of the task. Can be one of `pending`, `in_progress`, `done`, or `skipped`.
- `llm_hint`: A hint from the LLM on how to fix the issue.
- `metadata`: A dictionary of additional metadata about the task.

## GovernanceTaskGroup

A `GovernanceTaskGroup` is a collection of related `GovernanceTask` objects.

- `id`: A unique identifier for the group.
- `name`: The name of the group.
- `group_by`: The field that the tasks are grouped by.
- `tasks`: A list of `GovernanceTask` objects.

## GovernancePlan

A `GovernancePlan` is a collection of `GovernanceTaskGroup` objects.

- `project_name`: The name of the project.
- `created_at`: The date and time that the plan was created.
- `summary`: A summary of the plan.
- `groups`: A list of `GovernanceTaskGroup` objects.
