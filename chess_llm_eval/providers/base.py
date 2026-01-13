from typing import Any, Protocol


class LLMProvider(Protocol):
    """Protocol for LLM API providers."""

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> tuple[str, int, int]:
        """
        Send a completion request to the LLM.

        Args:
            messages: List of message dictionaries (role, content).
            model: Model identifier.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            **kwargs: Provider-specific arguments.

        Returns:
            Tuple containing (content, prompt_tokens, completion_tokens).

        Raises:
            Exception: If the API request fails.
        """
        ...
