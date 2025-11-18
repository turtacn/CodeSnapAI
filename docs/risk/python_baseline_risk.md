# Python Baseline Risk Assessment

This document outlines the methodology for the baseline risk assessment for Python projects in `codesage`.

## Overview

The baseline risk score is a simple, interpretable metric designed to identify high-risk files that may require additional attention. It is not intended to be a strict quality gate, but rather a tool for prioritizing code reviews, refactoring efforts, and testing.

## Risk Model

The risk score is calculated as a weighted average of several metrics, normalized to a scale of 0 to 1. The following metrics are used:

- **Maximum Cyclomatic Complexity**: The highest cyclomatic complexity of any function in the file.
- **Average Cyclomatic Complexity**: The average cyclomatic complexity of all functions in the file.
- **Fan-Out**: The number of other files that are imported by the current file.
- **Lines of Code (LOC)**: The total number of lines in the file.

### Default Weights and Thresholds

The default weights and thresholds are defined in `codesage/config/risk_baseline.py`:

- **Weights**:
    - `WEIGHT_COMPLEXITY_MAX`: 0.4
    - `WEIGHT_COMPLEXITY_AVG`: 0.3
    - `WEIGHT_FAN_OUT`: 0.2
    - `WEIGHT_LOC`: 0.1
- **Thresholds**:
    - `THRESHOLD_COMPLEXITY_HIGH`: 10
    - `THRESHOLD_RISK_MEDIUM`: 0.4
    - `THRESHOLD_RISK_HIGH`: 0.7

### Risk Levels

The risk score is used to assign a risk level to each file:

- **Low**: `risk_score < 0.4`
- **Medium**: `0.4 <= risk_score < 0.7`
- **High**: `risk_score >= 0.7`

## Factors

In addition to the risk score and level, `codesage` also identifies specific factors that contribute to a file's risk. These factors are included in the `FileRisk` model and can be used to quickly understand why a file is considered high-risk.

- `high_cyclomatic_complexity`: The file contains one or more functions with a cyclomatic complexity greater than the configured threshold.
- `high_fan_out`: The file imports a large number of other files.
- `large_file`: The file has a large number of lines of code.

## Limitations

This baseline risk assessment is a starting point and has several limitations:

- It does not consider code churn, test coverage, or other important risk factors.
- The weights and thresholds are based on general heuristics and may not be optimal for all projects.
- The fan-in/fan-out calculation is a simple count of imports and does not account for the nature of the dependencies.

Future versions of `codesage` may include more sophisticated risk models that address these limitations.
