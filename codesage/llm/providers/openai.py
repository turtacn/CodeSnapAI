from __future__ import annotations

import backoff
import openai
from openai import OpenAI, APIConnectionError, RateLimitError, APIStatusError

from codesage.config.llm import LLMConfig
from codesage.llm.client import BaseLLMClient, LLMRequest, LLMResponse


class OpenAIClient(BaseLLMClient):
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = OpenAI(api_key=config.api_key, timeout=config.timeout)

    @backoff.on_exception(
        backoff.expo,
        (RateLimitError, APIConnectionError, APIStatusError),
        max_tries=3,
        giveup=lambda e: isinstance(e, APIStatusError) and e.status_code not in [429, 500, 502, 503, 504],
    )
    def generate(self, request: LLMRequest) -> LLMResponse:
        messages = []
        if request.system_prompt or self.config.system_prompt:
            messages.append(
                {"role": "system", "content": request.system_prompt or self.config.system_prompt}
            )

        content = request.prompt
        if request.context:
            content += f"\n\nContext:\n{request.context}"

        messages.append({"role": "user", "content": content})

        response = self.client.chat.completions.create(
            model=request.model or self.config.model,
            messages=messages,
            temperature=self.config.temperature,
        )

        choice = response.choices[0]
        usage = response.usage

        usage_dict = {}
        if usage:
            usage_dict = {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
            }

        return LLMResponse(
            content=choice.message.content or "",
            usage=usage_dict,
            raw_output=str(response),
        )
