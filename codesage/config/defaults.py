from codesage.config.llm import LLMConfig
from codesage.config.snapshot_python_defaults import PythonSnapshotConfig
from codesage.config.rules_python_baseline import RulesPythonBaselineConfig
from codesage.config.ci import CIPolicyConfig
from codesage.config.governance import GovernanceConfig
from codesage.config.jules import JulesPromptConfig

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
    },
    "llm": LLMConfig.default().dict(),
    "ci": CIPolicyConfig.default().dict(),
    "governance": GovernanceConfig.default().dict(),
    "jules": JulesPromptConfig.default().dict(),
}
