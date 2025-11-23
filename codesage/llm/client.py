from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import backoff
import openai
import anthropic
from pydantic import BaseModel, Field


class LLMRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = None
    context: Optional[str] = None
    model: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    content: str
    usage: Dict[str, int] = Field(default_factory=dict)
    raw_output: Optional[str] = None


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generates a response from the LLM."""
        pass


class DummyLLMClient(BaseLLMClient):
    def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            content="```python\n# Dummy fix\ndef fixed_function():\n    pass\n```",
            usage={"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
            raw_output="Dummy output",
        )
