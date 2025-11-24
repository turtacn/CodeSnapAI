"""Sandbox Validator
Validates patch safety and correctness in an isolated environment.
"""
import ast
import subprocess
import tempfile
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    passed: bool = False
    checks: Dict[str, Dict] = field(default_factory=dict)

class SandboxValidator:
    """
    Patch Sandbox Validator

    Validation Levels:
    1. Syntax Check (AST Parse)
    2. Static Analysis (Linter)
    3. Unit Tests (if available)
    4. Type Checking (Python/TypeScript)
    """

    def validate_patch(
        self,
        patched_code: str,
        original_file: Path,
        validation_config: Dict
    ) -> ValidationResult:
        """
        Validates the patch in a sandbox.

        Args:
            patched_code: The code after applying the patch
            original_file: Path to the original file (for context/name)
            validation_config: Configuration for validation steps
                {
                    "run_tests": bool,
                    "run_linter": bool,
                    "run_type_check": bool,
                    "test_command": str
                }

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        # Create temporary sandbox directory
        with tempfile.TemporaryDirectory() as sandbox:
            sandbox_path = Path(sandbox)
            sandbox_file = sandbox_path / original_file.name
            sandbox_file.write_text(patched_code, encoding="utf-8")

            # Level 1: Syntax Check
            result.checks["syntax"] = self._check_syntax(sandbox_file)
            if not result.checks["syntax"]["passed"]:
                result.passed = False
                return result  # Fail fast

            # Level 2: Linter (Optional)
            if validation_config.get("run_linter"):
                result.checks["linter"] = self._run_linter(sandbox_file)

            # Level 3: Unit Tests (Optional)
            if validation_config.get("run_tests") and validation_config.get("test_command"):
                # Ideally, we need more than just the file to run tests (dependencies, other files).
                # A full sandbox copy of the project is expensive.
                # For now, we assume the test command runs in the project root but targets the sandboxed file
                # OR we copy necessary context.
                # The prompt implies running tests in `sandbox_dir`.
                # This suggests tests are self-contained or we copy everything.
                # Copying everything is safer but slow.
                # Let's assume for this phase we try to run isolated tests or if provided, use the sandbox as cwd.

                # NOTE: If tests depend on other files, they will fail if we only copy one file.
                # A better approach for real-world usage is copying the whole repo to sandbox
                # or using `overlayfs`.
                # For this task, we will follow the prompt's simplicity but acknowledge the limitation.

                result.checks["tests"] = self._run_tests(
                    sandbox,
                    validation_config["test_command"]
                )

            # Level 4: Type Check (Optional)
            if validation_config.get("run_type_check"):
                result.checks["type_check"] = self._run_type_checker(sandbox_file)

            # Aggregate Result
            # We consider passed if all executed checks passed.
            result.passed = all(
                check["passed"]
                for check in result.checks.values()
            )

        return result

    def _check_syntax(self, file_path: Path) -> Dict:
        """Syntax check using ast.parse"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                ast.parse(f.read())
            return {"passed": True, "errors": []}
        except SyntaxError as e:
            return {"passed": False, "errors": [str(e)]}
        except Exception as e:
            return {"passed": False, "errors": [f"Unexpected error: {e}"]}

    def _run_linter(self, file_path: Path) -> Dict:
        """Run Linter (Ruff)"""
        try:
            # We assume ruff is installed in the environment
            proc = subprocess.run(
                ["ruff", "check", str(file_path)],
                capture_output=True,
                text=True,
                timeout=10
            )
            return {
                "passed": proc.returncode == 0,
                "errors": proc.stdout.splitlines() if proc.returncode != 0 else []
            }
        except subprocess.TimeoutExpired:
            return {"passed": False, "errors": ["Linter timeout"]}
        except FileNotFoundError:
             return {"passed": False, "errors": ["Linter (ruff) not found"]}

    def _run_tests(self, sandbox_dir: str, test_command: str) -> Dict:
        """Run unit tests in isolated environment"""
        try:
            # Note: dependencies must be available in the environment where this runs
            proc = subprocess.run(
                test_command.split(),
                cwd=sandbox_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            return {
                "passed": proc.returncode == 0,
                "output": proc.stdout + proc.stderr
            }
        except subprocess.TimeoutExpired:
            return {"passed": False, "output": "Test timeout"}

    def _run_type_checker(self, file_path: Path) -> Dict:
        """Type check using mypy"""
        try:
            proc = subprocess.run(
                ["mypy", str(file_path)],
                capture_output=True,
                text=True,
                timeout=15
            )
            return {
                "passed": proc.returncode == 0,
                "errors": proc.stdout.splitlines() if proc.returncode != 0 else []
            }
        except subprocess.TimeoutExpired:
            return {"passed": False, "errors": ["Type checker timeout"]}
        except FileNotFoundError:
             return {"passed": False, "errors": ["Type checker (mypy) not found"]}
