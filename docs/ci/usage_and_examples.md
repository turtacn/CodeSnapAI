# CI Usage and Examples

This document provides examples of how to use the `codesage` tool in a CI/CD pipeline to generate reports and enforce quality gates.

## Generating Reports

You can generate reports in JSON, Markdown, and JUnit XML formats using the `codesage report` command.

```bash
codesage report \
  --input /path/to/snapshot.yaml \
  --out-json /path/to/report.json \
  --out-md /path/to/report.md \
  --out-junit /path/to/report.junit.xml
```

## Enforcing CI Policy

You can use the `--ci-policy-strict` flag to enforce a strict CI policy. If the policy fails, the command will exit with a non-zero exit code.

```bash
codesage report \
  --input /path/to/snapshot.yaml \
  --ci-policy-strict
```

This will fail the build if there are any error-level issues or high-risk files.
