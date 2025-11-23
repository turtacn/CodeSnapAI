from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    enabled: bool = Field(True, description="Enable or disable LLM suggestions.")
    provider: str = Field("dummy", description="The LLM provider to use.")
    model: str = Field("dummy-model", description="The LLM model to use.")
    api_key: Optional[str] = Field(None, description="The API key for the LLM provider.")
    temperature: float = Field(0.0, description="The temperature for LLM generation.")
    timeout: int = Field(60, description="Timeout in seconds for API calls.")
    retries: int = Field(3, description="Number of retries for failed API calls.")
    system_prompt: Optional[str] = Field(None, description="Custom system prompt.")

    max_issues_per_file: int = Field(10, description="The maximum number of issues to get suggestions for per file.")
    max_issues_per_run: int = Field(100, description="The maximum number of issues to get suggestions for per run.")
    filter_severity: List[str] = Field(
        default_factory=lambda: ["warning", "error"],
        description="Only get suggestions for issues with these severity levels.",
    )
    max_code_context_lines: int = Field(50, description="The maximum number of lines of code to include in the prompt.")

    @classmethod
    def default(cls) -> "LLMConfig":
        return cls()
