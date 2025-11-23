import subprocess
import os
import structlog
from typing import Dict, Optional, Tuple

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

            # If command is a string, we split it for safety if not using shell=True
            # But the user config provides a string template.
            # Ideally, we should parse it into arguments.
            # For this phase, we will switch to shell=False if list is provided,
            # but if string is provided, we might still need shell=True or shlex.split.
            # To address security, we use shlex.split if it's a string.
            import shlex
            if isinstance(command, str):
                args = shlex.split(command)
            else:
                args = command

            result = subprocess.run(
                args,
                shell=False, # Changed to False for security
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
