from codesage.config.llm import LLMConfig
from codesage.config.snapshot_python_defaults import PythonSnapshotConfig
from codesage.config.rules_python_baseline import RulesPythonBaselineConfig
from codesage.config.ci import CIPolicyConfig
from codesage.config.governance import GovernanceConfig
from codesage.config.jules import JulesPromptConfig
from codesage.config.web import WebConsoleConfig
from codesage.config.history import HistoryConfig
from codesage.config.org import OrgConfig
from codesage.config.policy import PolicyConfig
from codesage.config.audit import AuditConfig
from codesage.config.integrations import IntegrationsConfig

DEFAULT_CONFIG = {
    "languages": {
        "python": {"extensions": [".py"]},
        "go": {"extensions": [".go"]},
        "java": {"extensions": [".java"]},
        "javascript": {"extensions": [".js", "jsx"]},
        "typescript": {"extensions": [".ts", ".tsx"]},
    },
    "thresholds": {"complexity": 20, "duplication": 10},
    "ignore_paths": ["node_modules/", "vendor/", "tests/", "target/", "build/", ".gradle/", ".mvn/"],
    "snapshot": {
        "python": PythonSnapshotConfig().model_dump(),
    },
    "rules": {
        "python_baseline": RulesPythonBaselineConfig.default().model_dump(),
    },
    "llm": LLMConfig.default().model_dump(),
    "ci": CIPolicyConfig.default().model_dump(),
    "governance": GovernanceConfig.default().model_dump(),
    "jules": JulesPromptConfig.default().model_dump(),
    "web": WebConsoleConfig.default().model_dump(),
    "history": HistoryConfig.default().model_dump(),
    "org": OrgConfig.default().model_dump(),
    "policy": PolicyConfig().model_dump(),
    "audit": AuditConfig().model_dump(),
    "integrations": IntegrationsConfig().model_dump(),
}
