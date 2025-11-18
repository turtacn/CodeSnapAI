# Regression Detection

Regression detection helps you identify when changes to your codebase have a negative impact on code quality. It works by comparing the latest snapshot to a previous one and flagging significant increases in risk or issues.

## Rules

The regression detector uses the following rules by default:

- **High-risk files increase:** A warning is triggered if the number of high-risk files increases by more than a configured threshold.
- **Error issues increase:** An error is triggered if the number of error-level issues increases by more than a configured threshold.

## Integration with CI

Regression warnings can be integrated into your CI pipeline. When enabled, the `codesage report` command will include a summary of any regression warnings. This allows you to be notified of potential regressions without necessarily failing the build.

To enable regression detection in CI, configure the `history` and `ci` sections in your `.codesage.yaml` file.
