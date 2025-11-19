from pathlib import Path
import pytest
from codesage.policy.parser import load_policy
from codesage.policy.dsl_models import PolicySet

def test_parse_basic_policy_file(tmp_path: Path):
    policy_content = """
rules:
  - id: "high_risk_alert"
    scope: "project"
    conditions:
      - field: "high_risk_files"
        op: ">"
        value: 0
    actions:
      - type: "raise_warning"
        params: {category: "risk"}
"""
    policy_file = tmp_path / "policy.yaml"
    policy_file.write_text(policy_content)

    policy_set = load_policy(policy_file)
    assert isinstance(policy_set, PolicySet)
    assert len(policy_set.rules) == 1
    rule = policy_set.rules[0]
    assert rule.id == "high_risk_alert"
    assert rule.scope == "project"
    assert len(rule.conditions) == 1
    condition = rule.conditions[0]
    assert condition.field == "high_risk_files"
    assert condition.op == ">"
    assert condition.value == 0
    assert len(rule.actions) == 1
    action = rule.actions[0]
    assert action.type == "raise_warning"
    assert action.params == {"category": "risk"}

def test_invalid_policy_file_raises_error(tmp_path: Path):
    policy_content = """
rules:
  - id: "invalid_rule"
    scope: "project"
    conditions:
      - field: "high_risk_files"
        op: "is_greater_than" # invalid op
        value: 0
    actions:
      - type: "raise_warning"
"""
    policy_file = tmp_path / "policy.yaml"
    policy_file.write_text(policy_content)

    with pytest.raises(ValueError):
        load_policy(policy_file)
