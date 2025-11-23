from pathlib import Path
from codesage.config.governance import GovernanceConfig
from codesage.governance.sandbox import Sandbox
from codesage.analyzers.semantic.models import DependencyGraph
import structlog
from dataclasses import dataclass
from typing import Optional, List, Set

logger = structlog.get_logger()

@dataclass
class ValidationResult:
    success: bool
    error: str = ""
    stage: str = ""

class CodeValidator:
    def __init__(self, config: GovernanceConfig, sandbox: Optional[Sandbox] = None):
        self.config = config
        self.sandbox = sandbox or Sandbox(timeout=getattr(config, 'execution_timeout', 30))

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

        # 2. Test Execution
        # If scope is provided, use generic command template.
        # If not, try to resolve related tests? No, validation is usually explicit.
        # But Phase 1 says "In Validator... implement resolve_related_tests".
        # This method is likely called by the orchestrator, OR we can try to resolve here if scope is missing.
        # But validate usually receives the scope.

        # We assume scope is passed. If not, maybe we skip.
        if related_test_scope:
             # If related_test_scope is a list of files (space separated string maybe?), we might want to use run_tests directly
             # But config.validation.test_commands expects a string template.
             # If we want to leverage Sandbox.run_tests, we should check if we can.

             # Check if we can use the intelligent sandbox runner
             # But the config based approach is more flexible for users.
             # However, for "Intelligent Governance Loop", we want `run_tests` to be used.
             # Let's see if we can detect if we should use the new logic.

             # If `related_test_scope` looks like a file list or we decide to use the new method:
             # The prompt says: "Sandbox... auto construct test command".
             # So we should probably prefer Sandbox.run_tests if we have a list of files.
             pass

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

    def resolve_related_tests(self, source_file: str, dependency_graph: DependencyGraph) -> List[str]:
        """
        Identifies test files that depend on or test the source_file.
        """
        related_tests: Set[str] = set()

        # 1. Naming Convention (Direct tests)
        # Python: test_foo.py tests foo.py (or tests/test_foo.py)
        # Go: foo_test.go tests foo.go
        path = Path(source_file)
        if path.suffix == '.py':
            # Check sibling
            sibling_test = path.parent / f"test_{path.name}"
            if sibling_test.exists(): # This check requires file access, maybe relative path logic is safer
                related_tests.add(str(sibling_test))

            sibling_test_2 = path.parent / f"test_{path.stem}.py" # Same as above but consistent
            if sibling_test_2.exists():
                 related_tests.add(str(sibling_test_2))

            # Check tests/ folder in project root or relative?
            # This is hard without project root. We assume relative paths.
            # Common pattern: tests/test_{name}.py or tests/unit/test_{name}.py
            # Since we don't know the project root here easily without more context,
            # we rely on the dependency graph primarily for "distant" tests.

        elif path.suffix == '.go':
            sibling_test = path.with_name(f"{path.stem}_test.go")
            if sibling_test.exists():
                related_tests.add(str(sibling_test))

        # 2. Dependency Graph (Reverse lookup)
        # We need to find all nodes that have an edge TO source_file
        # edges is List[Tuple[source, target]] -> source imports target.
        # We want X where X imports source_file.

        # Build reverse map if graph is large, or iterate.
        # Edges: (importer, imported)
        # We look for (importer, source_file)

        importers = [u for u, v in dependency_graph.edges if v == source_file]

        for importer in importers:
            if self._is_test_file(importer):
                related_tests.add(importer)
            else:
                # Optional: Transitive?
                # If A imports Source, and TestA imports A, maybe TestA should run?
                # For P1, let's stick to direct importers that are tests.
                pass

        return list(related_tests)

    def _is_test_file(self, file_path: str) -> bool:
        return (
            file_path.endswith("_test.go") or
            file_path.startswith("test_") or
            "/test_" in file_path or
            "/tests/" in file_path or
            file_path.endswith("_test.py") # convention
        )
