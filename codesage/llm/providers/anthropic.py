from __future__ import annotations

import backoff
import anthropic
from anthropic import Anthropic, APIConnectionError, RateLimitError, APIStatusError

from codesage.config.llm import LLMConfig
from codesage.llm.client import BaseLLMClient, LLMRequest, LLMResponse


class AnthropicClient(BaseLLMClient):
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = Anthropic(api_key=config.api_key, timeout=config.timeout)

    @backoff.on_exception(
        backoff.expo,
        (RateLimitError, APIConnectionError, APIStatusError),
        max_tries=3,
        giveup=lambda e: isinstance(e, APIStatusError) and e.status_code not in [429, 500, 502, 503, 504],
    )
    def generate(self, request: LLMRequest) -> LLMResponse:
        system = request.system_prompt or self.config.system_prompt

        content = request.prompt
        if request.context:
            content += f"\n\nContext:\n{request.context}"

        messages = [{"role": "user", "content": content}]

        kwargs = {
            "model": request.model or self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": 4096,  # Default max tokens for Claude
        }

        if system:
            kwargs["system"] = system

        response = self.client.messages.create(**kwargs)

        content_text = ""
        for block in response.content:
            if block.type == "text":
                content_text += block.text

        usage_dict = {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
        }

        return LLMResponse(
            content=content_text,
            usage=usage_dict,
            raw_output=str(response),
        )
