import subprocess
import os
import structlog
import shlex
from typing import Dict, Optional, Tuple, List

logger = structlog.get_logger()

class Sandbox:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def run(self, command: str | list[str], env: Optional[Dict[str, str]] = None, cwd: Optional[str] = None) -> Tuple[bool, str]:
        """
        Runs a command in a subprocess.
        Returns (success, output).
        """
        try:
            # Simple environment isolation: inherit mainly PATH, but could restrict others.
            run_env = os.environ.copy()
            if env:
                run_env.update(env)

            if isinstance(command, str):
                args = shlex.split(command)
            else:
                args = command

            result = subprocess.run(
                args,
                shell=False,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=run_env,
                cwd=cwd
            )

            output = result.stdout + result.stderr
            if result.returncode != 0:
                return False, output
            return True, output

        except subprocess.TimeoutExpired:
            logger.error("Sandbox execution timed out", command=command)
            return False, "Execution timed out"
        except Exception as e:
            logger.error("Sandbox execution failed", command=command, error=str(e))
            return False, str(e)

    def run_tests(self, test_files: List[str], language: str) -> Tuple[bool, str]:
        """
        Executes tests for the given language and test files.
        Automatically constructs the test command.
        """
        if not test_files:
            return True, "No test files to run."

        command = []
        if language == "python":
            # Assuming pytest is available in the environment
            command = ["pytest"] + test_files
        elif language == "go":
            # Go tests run per package usually, but can target files if in same package.
            # Best practice is `go test ./pkg/...` or `go test path/to/file_test.go`
            # However, `go test file.go` requires passing all files in the package.
            # Safer to find the directory of the test file and run `go test -v ./path/to/dir`
            # But if multiple directories, we need multiple commands or one `go test ./...` with patterns.

            # For simplicity, let's group by directory
            dirs = set(os.path.dirname(f) for f in test_files)
            if len(dirs) == 1:
                # Single directory
                d = list(dirs)[0]
                # If d is empty (current dir), use "."
                target = d if d else "."
                if not target.startswith(".") and not os.path.isabs(target):
                    target = "./" + target
                command = ["go", "test", "-v", target]
            else:
                # Multiple directories - run for each? Or just list them?
                # Go test accepts multiple packages.
                targets = []
                for d in dirs:
                    target = d if d else "."
                    if not target.startswith(".") and not os.path.isabs(target):
                        target = "./" + target
                    targets.append(target)
                command = ["go", "test", "-v"] + targets
        else:
            return False, f"Unsupported language for test execution: {language}"

        logger.info("Running tests", language=language, command=command)
        return self.run(command)
