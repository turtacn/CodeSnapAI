from setuptools import setup, find_packages

setup(
    name="codesage",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click",
        "pyyaml",
        "tree-sitter",
        "structlog",
        "gitignore-parser",
    ],
    entry_points={
        "console_scripts": [
            "codesage = codesage.cli.main:cli",
        ],
    },
)
