from pathlib import Path
from codesage.config.governance import GovernanceConfig
from codesage.governance.sandbox import Sandbox
import structlog
from dataclasses import dataclass
from typing import Optional

logger = structlog.get_logger()

@dataclass
class ValidationResult:
    success: bool
    error: str = ""
    stage: str = ""

class CodeValidator:
    def __init__(self, config: GovernanceConfig, sandbox: Optional[Sandbox] = None):
        self.config = config
        self.sandbox = sandbox or Sandbox()

    def validate(self, file_path: Path, language: str, related_test_scope: Optional[str] = None) -> ValidationResult:
        # 1. Syntax Check
        syntax_cmd_template = self.config.validation.syntax_commands.get(language)
        if syntax_cmd_template:
            cmd = syntax_cmd_template.format(file=str(file_path))
            logger.info("Running syntax check", command=cmd)
            success, output = self.sandbox.run(cmd)
            if not success:
                logger.warning("Syntax validation failed", file=str(file_path), error=output)
                return ValidationResult(success=False, error=output, stage="syntax")

        # 2. Test Execution (Optional)
        # Only run if a scope is provided. In real world, we might infer it.
        if related_test_scope:
             test_cmd_template = self.config.validation.test_commands.get(language)
             if test_cmd_template:
                 cmd = test_cmd_template.format(scope=related_test_scope)
                 logger.info("Running test check", command=cmd)
                 success, output = self.sandbox.run(cmd)
                 if not success:
                     logger.warning("Test validation failed", file=str(file_path), scope=related_test_scope, error=output)
                     return ValidationResult(success=False, error=output, stage="test")

        return ValidationResult(success=True)
