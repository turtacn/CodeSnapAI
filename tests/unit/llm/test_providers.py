import pytest
from unittest.mock import MagicMock, patch

from codesage.config.llm import LLMConfig
from codesage.llm.client import LLMRequest
from codesage.llm.providers.openai import OpenAIClient
from codesage.llm.providers.anthropic import AnthropicClient
from openai import APIStatusError, RateLimitError
from anthropic import APIStatusError as AnthropicAPIStatusError


@pytest.fixture
def llm_config():
    return LLMConfig(
        provider="openai",
        api_key="test-key",
        model="gpt-4",
        temperature=0.1
    )


class TestOpenAIClient:
    def test_openai_client_success(self, llm_config):
        with patch("codesage.llm.providers.openai.OpenAI") as mock_openai:
            mock_instance = mock_openai.return_value
            mock_response = MagicMock()
            mock_choice = MagicMock()
            mock_choice.message.content = "Fixed code"
            mock_response.choices = [mock_choice]
            mock_response.usage.prompt_tokens = 10
            mock_response.usage.completion_tokens = 5
            mock_response.usage.total_tokens = 15
            mock_instance.chat.completions.create.return_value = mock_response

            client = OpenAIClient(llm_config)
            request = LLMRequest(prompt="Fix this")
            response = client.generate(request)

            assert response.content == "Fixed code"
            assert response.usage["total_tokens"] == 15
            mock_instance.chat.completions.create.assert_called_once()

    def test_openai_client_retry(self, llm_config):
        with patch("codesage.llm.providers.openai.OpenAI") as mock_openai:
            mock_instance = mock_openai.return_value

            # Mock raising RateLimitError twice, then success
            error_response = MagicMock()
            error_response.status_code = 429
            error_response.headers = {"retry-after": "0.01"} # Speed up test

            # Note: backoff retries based on exception class.
            # We simulate RateLimitError. OpenAI's RateLimitError requires response/body/message in constructor usually,
            # but we can just mock the side_effect.

            # We need to construct a proper exception object or mock it effectively
            rl_error = RateLimitError(
                message="Rate limit",
                response=error_response,
                body=None
            )

            mock_success_response = MagicMock()
            mock_success_response.choices[0].message.content = "Success"

            mock_instance.chat.completions.create.side_effect = [rl_error, rl_error, mock_success_response]

            client = OpenAIClient(llm_config)
            request = LLMRequest(prompt="Fix this")

            # We use a small wait generator or patch sleep to avoid waiting in tests if possible.
            # But backoff is hard to patch without configuring it.
            # For unit test, we just assert it eventually succeeds.
            # However, default backoff is exponential. We might want to reduce max_tries in test config if possible
            # or just rely on the logic.

            response = client.generate(request)
            assert response.content == "Success"
            assert mock_instance.chat.completions.create.call_count == 3


class TestAnthropicClient:
    def test_anthropic_client_success(self, llm_config):
        llm_config.provider = "anthropic"
        with patch("codesage.llm.providers.anthropic.Anthropic") as mock_anthropic:
            mock_instance = mock_anthropic.return_value
            mock_response = MagicMock()
            mock_block = MagicMock()
            mock_block.type = "text"
            mock_block.text = "Claude Fix"
            mock_response.content = [mock_block]
            mock_response.usage.input_tokens = 10
            mock_response.usage.output_tokens = 5

            mock_instance.messages.create.return_value = mock_response

            client = AnthropicClient(llm_config)
            request = LLMRequest(prompt="Fix this")
            response = client.generate(request)

            assert response.content == "Claude Fix"
            assert response.usage["completion_tokens"] == 5
            mock_instance.messages.create.assert_called_once()
