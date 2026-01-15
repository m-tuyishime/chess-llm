from unittest.mock import AsyncMock, MagicMock

import pytest

from chess_llm_eval.providers.nim import NIMProvider


@pytest.fixture
def mock_openai_client() -> AsyncMock:
    """Mock AsyncOpenAI client."""
    client = AsyncMock()
    # Mock the chat.completions.create method
    client.chat.completions.create = AsyncMock()
    return client


@pytest.fixture
def nim_provider(mock_openai_client: AsyncMock) -> NIMProvider:
    """Create NIMProvider with mocked client."""
    provider = NIMProvider(api_key="test_key")
    provider.client = mock_openai_client
    return provider


@pytest.mark.asyncio
async def test_nim_complete_success(
    nim_provider: NIMProvider, mock_openai_client: AsyncMock
) -> None:
    """
    Test successful API completion request.
    Why: Verifies that our provider correctly wraps the OpenAI client, passes arguments
    (like messages), and parses the response content and usage stats.
    """
    # Setup mock response
    mock_choice = MagicMock()
    mock_choice.message.content = "<FinalMove>e4</FinalMove>"

    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 10
    mock_usage.completion_tokens = 20

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_completion.usage = mock_usage

    mock_openai_client.chat.completions.create.return_value = mock_completion

    content, pt, ct = await nim_provider.complete(
        [{"role": "user", "content": "make a move"}], model="meta/llama-3.1-8b-instruct"
    )

    assert content == "<FinalMove>e4</FinalMove>"
    assert pt == 10
    assert ct == 20


@pytest.mark.asyncio
async def test_nim_complete_empty_response(
    nim_provider: NIMProvider, mock_openai_client: AsyncMock
) -> None:
    """
    Test handling of empty API responses.
    Why: External APIs can fail or return malformed data. We ensure that such cases
    raise an appropriate exception instead of failing silently.
    """
    # Setup mock response with no choices
    mock_completion = MagicMock()
    mock_completion.choices = []

    mock_openai_client.chat.completions.create.return_value = mock_completion

    with pytest.raises(ValueError, match="Empty response"):
        await nim_provider.complete(
            [{"role": "user", "content": "make a move"}], model="meta/llama-3.1-8b-instruct"
        )


def test_nim_provider_requires_api_key() -> None:
    """
    Test that NIMProvider raises error when API key is not provided.
    Why: The provider cannot function without an API key, so we should fail fast
    with a clear error message rather than waiting for the first API call to fail.
    """
    import os

    # Temporarily remove env var if it exists
    old_key = os.environ.pop("NIM_API_KEY", None)
    try:
        with pytest.raises(ValueError, match="NIM_API_KEY not provided"):
            NIMProvider()
    finally:
        # Restore env var
        if old_key:
            os.environ["NIM_API_KEY"] = old_key
