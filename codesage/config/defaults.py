from codesage.config.snapshot_python_defaults import PythonSnapshotConfig
from codesage.config.rules_python_baseline import RulesPythonBaselineConfig

DEFAULT_CONFIG = {
    "languages": {
        "python": {"extensions": [".py"]},
        "go": {"extensions": [".go"]},
        "javascript": {"extensions": [".js", "jsx"]},
        "typescript": {"extensions": [".ts", ".tsx"]},
    },
    "thresholds": {"complexity": 20, "duplication": 10},
    "ignore_paths": ["node_modules/", "vendor/", "tests/"],
    "snapshot": {
        "python": PythonSnapshotConfig().dict(),
    },
    "rules": {
        "python_baseline": RulesPythonBaselineConfig.default().dict(),
    }
}
