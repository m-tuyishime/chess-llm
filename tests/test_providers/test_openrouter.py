from unittest.mock import AsyncMock, MagicMock

import pytest

from chess_llm_eval.providers.openrouter import OpenRouterProvider


@pytest.fixture
def mock_openai_client() -> AsyncMock:
    client = AsyncMock()
    # Mock the chat.completions.create method
    client.chat.completions.create = AsyncMock()
    return client


@pytest.fixture
def openrouter_provider(mock_openai_client: AsyncMock) -> OpenRouterProvider:
    provider = OpenRouterProvider("https://test.url", "key")
    provider.client = mock_openai_client
    return provider


@pytest.mark.asyncio
async def test_openrouter_complete_success(
    openrouter_provider: OpenRouterProvider, mock_openai_client: AsyncMock
) -> None:
    """
    Test successful API completion request.
    Why: Verifies that our provider correctly wraps the OpenAI client, passes arguments
    (like messages and extra_body), and parses the response content and usage stats.
    """
    # Setup mock response
    mock_choice = MagicMock()
    mock_choice.message.content = "Evaluated move"

    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 10
    mock_usage.completion_tokens = 20

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_completion.usage = mock_usage

    mock_openai_client.chat.completions.create.return_value = mock_completion

    content, pt, ct = await openrouter_provider.complete(
        [{"role": "user", "content": "hi"}], model="test-model"
    )

    assert content == "Evaluated move"
    assert pt == 10
    assert ct == 20

    # Verify extra_body logic
    call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
    assert call_kwargs["extra_body"]["include_usage"] is True


@pytest.mark.asyncio
async def test_openrouter_complete_empty_response(
    openrouter_provider: OpenRouterProvider, mock_openai_client: AsyncMock
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
        await openrouter_provider.complete([{"role": "user", "content": "hi"}], model="test-model")
