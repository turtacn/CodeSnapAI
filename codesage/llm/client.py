from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class LLMRequest(BaseModel):
    prompt: str
    model: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    fix_hint: str
    rationale: Optional[str] = None
    raw_output: Optional[str] = None


class LLMClient(ABC):
    @abstractmethod
    def generate(self, request: LLMRequest) -> LLMResponse:
        ...


class DummyLLMClient(LLMClient):
    def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            fix_hint="Consider refactoring this code to reduce complexity and improve readability.",
            rationale="This issue indicates high complexity or missing typing; smaller functions and explicit types can help.",
            raw_output=None,
        )
