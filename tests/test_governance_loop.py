import pytest
from pathlib import Path
from unittest.mock import MagicMock
from datetime import datetime
from codesage.governance.task_orchestrator import TaskOrchestrator
from codesage.governance.task_models import GovernancePlan, GovernanceTask, GovernanceTaskGroup
from codesage.llm.client import BaseLLMClient, LLMResponse
from codesage.config.governance import GovernanceConfig
from codesage.governance.sandbox import Sandbox

class MockSandbox(Sandbox):
    def __init__(self):
        super().__init__()
        self.calls = []

    def run(self, command: str, env=None, cwd=None):
        self.calls.append(command)
        # We don't implement logic here because we will patch 'run' in the test
        return True, ""

@pytest.fixture
def mock_llm_client():
    client = MagicMock(spec=BaseLLMClient)
    # First response: bad code (trigger syntax error)
    # Second response: good code
    client.generate.side_effect = [
        LLMResponse(content="```python\ndef foo()\n    pass\n```"), # Missing colon
        LLMResponse(content="```python\ndef foo():\n    pass\n```"), # Correct
    ]
    return client

def test_governance_loop_rollback_and_retry(tmp_path, mock_llm_client):
    # Setup file
    target_file = tmp_path / "test_file.py"
    target_file.write_text("def foo():\n    pass\n")

    # Setup Plan and Task
    task = GovernanceTask(
        id="task-1",
        project_name="test_project",
        file_path=str(target_file),
        language="python",
        rule_id="R1",
        description="Fix style",
        risk_level="low",
        priority=1
    )
    group = GovernanceTaskGroup(
        id="g1",
        name="g1",
        group_by="rule",
        tasks=[task]
    )
    plan = GovernancePlan(
        project_name="test_project",
        created_at=datetime.utcnow(),
        summary={},
        groups=[group]
    )

    # Setup Config
    config = GovernanceConfig()

    # Initialize Orchestrator
    orchestrator = TaskOrchestrator(plan, llm_client=mock_llm_client, config=config)

    # Inject Mock Sandbox
    mock_sandbox = MockSandbox()
    orchestrator.validator.sandbox = mock_sandbox

    # Define side effect for sandbox.run
    # 1st run: Syntax check on file with "def foo()" -> Fail
    # 2nd run: Syntax check on file with "def foo():" -> Pass
    def side_effect_run(command, env=None, cwd=None):
        mock_sandbox.calls.append(command)
        content = target_file.read_text()
        if "def foo()\n" in content:
             return False, "SyntaxError: invalid syntax"
        return True, ""

    mock_sandbox.run = side_effect_run

    result = orchestrator.execute_task(task, apply_fix=True)

    assert result is True
    assert task.status == "done"
    assert "def foo():" in target_file.read_text()
    assert not (tmp_path / "test_file.py.bak").exists() # Backup cleaned up

    # Verify LLM was called twice
    assert mock_llm_client.generate.call_count == 2

    # Verify the second prompt contained the error
    call_args_list = mock_llm_client.generate.call_args_list
    second_call_prompt = call_args_list[1][0][0].prompt
    assert "Previous attempt failed validation" in second_call_prompt
    assert "SyntaxError" in second_call_prompt
