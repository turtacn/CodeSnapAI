# Contributing to CodeSage

We welcome contributions from the community! Please read this guide to learn how you can help.

## Code of Conduct

This project and everyone participating in it is governed by the [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How to Contribute

- **Reporting Bugs:** If you find a bug, please open an issue and provide as much detail as possible.
- **Suggesting Enhancements:** If you have an idea for a new feature, open an issue to discuss it.
- **Pull Requests:** We welcome pull requests. Please make sure your code follows the project's style guidelines and that all tests pass.

## Development Setup

1.  Fork the repository.
2.  Clone your fork: `git clone https://github.com/your-username/codesage.git`
3.  Install dependencies: `pip install -e .[dev]`
4.  Set up pre-commit hooks: `pre-commit install`

## Style Guide

We use `black` for code formatting and `ruff` for linting. Please make sure your code conforms to these standards by running `pre-commit run --all-files` before submitting a pull request.
