# Semantic Analysis

This document details the architecture of the semantic analysis engine and provides guidance on how to extend it with new rules.

## Architecture

The semantic analysis engine is composed of several analyzers, each responsible for a specific dimension of analysis:

- **Complexity Analyzer**: Calculates cyclomatic complexity, cognitive complexity, and Halstead metrics.
- **Dependency Analyzer**: Builds a dependency graph of the project, detects circular dependencies, and calculates dependency depth.
- **Pattern Analyzer**: Detects design patterns and anti-patterns in the code.

The analysis process is orchestrated by a central pipeline that runs each analyzer in sequence and aggregates the results.

## Extending the Engine

The engine can be extended by adding new analysis rules. Each rule is a Python class that inherits from a base rule class and implements a `check` method.

### Adding a new Complexity Rule

To add a new complexity rule, create a new class in `codesage/analyzers/semantic/rules/complexity_rules.py` that inherits from `ComplexityRule` and implement the `check` method.

### Adding a new Dependency Rule

To add a new dependency rule, create a new class in `codesage/analyzers/semantic/rules/dependency_rules.py` that inherits from `DependencyRule` and implement the `check` method.

### Adding a new Pattern Rule

To add a new pattern rule, create a new class in `codesage/analyzers/semantic/rules/pattern_rules.py` that inherits from `PatternRule` and implement the `match` method. This method should use a tree-sitter query to find matching nodes in the AST.
