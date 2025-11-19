from typing import Any, List, Dict, Literal
from pydantic import BaseModel, Field, field_validator

class PolicyCondition(BaseModel):
    field: str = Field(..., description="The field to evaluate, e.g., 'risk_level' or 'error_issues_delta'.")
    op: str = Field(..., description="The comparison operator.")
    value: Any = Field(..., description="The value to compare against.")

    @field_validator('op')
    @classmethod
    def op_must_be_valid(cls, v: str) -> str:
        """Validate that the operator is one of the allowed values."""
        valid_ops = {"==", "!=", ">", "<", ">=", "<=", "in", "not in"}
        if v not in valid_ops:
            raise ValueError(f"Operator '{v}' is not valid. Must be one of {sorted(list(valid_ops))}")
        return v

class PolicyAction(BaseModel):
    type: str = Field(..., description="The type of action to take, e.g., 'raise_warning'.")
    params: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the action.")

class PolicyRule(BaseModel):
    id: str = Field(..., description="A unique identifier for the policy rule.")
    scope: Literal["project", "file", "org"] = Field(..., description="The scope at which the rule is evaluated.")
    conditions: List[PolicyCondition] = Field(..., description="A list of conditions that must all be met for the rule to trigger.")
    actions: List[PolicyAction] = Field(..., description="A list of actions to take if the conditions are met.")

class PolicySet(BaseModel):
    rules: List[PolicyRule] = Field(..., description="A list of policy rules.")

class PolicyDecision(BaseModel):
    rule_id: str = Field(..., description="The ID of the rule that was triggered.")
    scope: str = Field(..., description="The scope of the decision (e.g., 'project').")
    target: str = Field(..., description="The identifier of the target (e.g., project name).")
    severity: str = Field(..., description="The severity of the decision (e.g., 'warning', 'error').")
    actions: List[PolicyAction] = Field(..., description="The actions to be taken.")
    reason: str = Field(..., description="A description of why the decision was made.")
