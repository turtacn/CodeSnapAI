from __future__ import annotations

from codesage.config.llm import LLMConfig
from codesage.llm.client import BaseLLMClient, DummyLLMClient
from codesage.llm.providers.openai import OpenAIClient
from codesage.llm.providers.anthropic import AnthropicClient


class LLMFactory:
    @staticmethod
    def create_client(config: LLMConfig) -> BaseLLMClient:
        if config.provider == "openai":
            return OpenAIClient(config)
        elif config.provider == "anthropic":
            return AnthropicClient(config)
        elif config.provider == "dummy":
            return DummyLLMClient()
        else:
            raise ValueError(f"Unsupported LLM provider: {config.provider}")
