from pydantic import BaseModel, Field


class JulesPromptConfig(BaseModel):
    """Jules prompt configuration."""

    max_code_context_lines: int = Field(
        100, description="Maximum number of lines of code to include in the prompt."
    )
    default_language: str = Field(
        "en", description="The default natural language for the prompt."
    )
    include_llm_hint: bool = Field(
        True, description="Whether to include the LLM hint in the prompt."
    )

    @classmethod
    def default(cls) -> "JulesPromptConfig":
        """Return the default Jules prompt configuration."""
        return cls()
