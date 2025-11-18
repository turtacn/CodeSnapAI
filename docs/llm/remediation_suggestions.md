# LLM-Assisted Remediation Suggestions

This document outlines the design and usage of the LLM-assisted remediation suggestions feature in CodeSage.

## Design Goals and Boundaries

The primary goal of this feature is to enrich the `ProjectSnapshot` with valuable, context-aware suggestions for fixing issues identified by the rule engine. It is important to note the following boundaries:

- **Suggestions, not Autofixes:** The feature provides suggestions for remediation, not automatic code fixes. It is up to the developer to implement the suggested changes.
- **No Code Modification:** The feature does not modify the source code in any way. It only enriches the snapshot data.
- **No CI/CD Integration:** The feature is not intended to be used in a CI/CD pipeline for automatic code modification.

## Data Flow

The data flow for this feature is as follows:

1. **Input:** A `ProjectSnapshot` YAML file containing a list of issues.
2. **Processing:**
   - The `llm-suggest` CLI command is invoked with the input snapshot file.
   - The command iterates through the issues in the snapshot and filters them based on the configured severity levels.
   - For each filtered issue, a prompt is constructed containing the issue details, code snippet, and other relevant context.
   - The prompt is sent to the configured LLM client, which returns a remediation suggestion.
   - The suggestion is added to the `Issue` object in the snapshot.
3. **Output:** A new `ProjectSnapshot` YAML file is generated with the enriched issue data.

## Field Explanations

The following fields are added to the `Issue` model to support this feature:

- `llm_fix_hint`: A brief, actionable suggestion for fixing the issue.
- `llm_rationale`: A brief explanation of why the suggested fix is recommended.
- `llm_status`: The status of the LLM suggestion. Can be one of `not_requested`, `requested`, `succeeded`, or `failed`.
- `llm_model`: The name of the LLM model used to generate the suggestion.
- `llm_last_updated_at`: The timestamp when the suggestion was last updated.

The following field is added to the `ProjectSnapshot` model:

- `llm_stats`: An object containing statistics about the LLM calls made during the enrichment process.

## CLI Usage

The `llm-suggest` command is used to enrich a snapshot with LLM-powered suggestions.

### Example

```bash
codesage llm-suggest \\
    --input /path/to/snapshot.yaml \\
    --output /path/to/enriched_snapshot.yaml \\
    --provider dummy \\
    --model dummy-model
```
