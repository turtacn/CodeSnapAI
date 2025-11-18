# CodeSage Web Console API Reference

This document provides a reference for the RESTful API provided by the CodeSage web console.

## Project

### `GET /api/project/summary`

Returns a summary of the project, including statistics about files, languages, risks, and issues.

**Response Body:**

```json
{
  "project_name": "string",
  "total_files": "integer",
  "languages": ["string"],
  "files_per_language": {
    "string": "integer"
  },
  "high_risk_files": "integer",
  "total_issues": "integer"
}
```

## Files

### `GET /api/files`

Returns a list of all files in the project. Supports filtering by language and risk level.

**Query Parameters:**

-   `language` (optional): The language to filter by (e.g., `python`).
-   `risk_level` (optional): The risk level to filter by (e.g., `high`).

**Response Body:**

```json
[
  {
    "path": "string",
    "language": "string",
    "risk_level": "string",
    "risk_score": "number",
    "issues_total": "integer"
  }
]
```

### `GET /api/files/{path}`

Returns detailed information about a single file.

**Response Body:**

```json
{
  "path": "string",
  "language": "string",
  "metrics": {},
  "risk": {},
  "issues": []
}
```

## Governance Plan

### `GET /api/governance/plan`

Returns the governance plan for the project.

### `GET /api/governance/tasks/{task_id}`

Returns detailed information about a single governance task.

### `GET /api/governance/tasks/{task_id}/jules-prompt`

Returns a Jules prompt for the specified governance task.
