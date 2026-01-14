from unittest.mock import AsyncMock

import pytest

from chess_llm_eval.agents.llm import LLMAgent
from chess_llm_eval.providers.base import LLMProvider


@pytest.fixture
def mock_provider() -> AsyncMock:
    return AsyncMock(spec=LLMProvider)


@pytest.fixture
def llm_agent(mock_provider: AsyncMock) -> LLMAgent:
    return LLMAgent(provider=mock_provider, model_name="test-model")


def test_llm_agent_create_messages(llm_agent: LLMAgent) -> None:
    """
    Test prompt construction.
    Why: The prompt is the interface to the LLM. If we don't construct the context,
    history, and instructions correctly, the LLM will fail to solve the puzzle or
    output invalid formats.
    """
    messages = llm_agent._create_messages("fen_string_123", ["e4", "d4"], "white")
    assert len(messages) == 2

    # Verify System Prompt
    system_content = messages[0]["content"]
    assert messages[0]["role"] == "system"
    assert "You are a chess engine" in system_content
    assert "white" in system_content
    # Ensure critical formatting instructions are present
    assert "<FinalMove>" in system_content
    assert "Think step-by-step" in system_content

    # Verify User Prompt
    user_content = messages[1]["content"]
    assert messages[1]["role"] == "user"
    assert "FEN: fen_string_123" in user_content
    # Check that legal moves are formatted as a comma-separated list or similar
    assert "e4" in user_content
    assert "d4" in user_content
    assert "Legal Moves: e4, d4" in user_content


def test_llm_agent_parse_move(llm_agent: LLMAgent) -> None:
    """
    Test parsing moves from LLM output.
    Why: LLMs are robust but chatty. We rely on tags (e.g., <FinalMove>) or specific formats.
    This test ensures our regex/parsing logic correctly isolates the move string.
    """
    assert llm_agent._parse_move("<FinalMove>e4</FinalMove>") == "e4"
    assert llm_agent._parse_move("Thinking... <FinalMove>Nf3+</FinalMove>") == "Nf3+"
    assert llm_agent._parse_move("No tags here") is None


@pytest.mark.asyncio
async def test_llm_agent_get_move_success(llm_agent: LLMAgent, mock_provider: AsyncMock) -> None:
    """
    Test the full get_move flow (prompt -> provider -> parse).
    Why: This is the main public method of the agent. We need to ensure that it orchestrates
    the internal steps correctly and returns the move logic (plus token usage).
    """
    mock_provider.complete.return_value = ("<FinalMove>e4</FinalMove>", 10, 5)
    result = await llm_agent.get_move("fen", ["e4"], "white")
    assert result is not None
    move, pt, ct = result
    assert move == "e4"
    assert pt == 10
    assert ct == 5


@pytest.mark.asyncio
async def test_llm_agent_get_move_parse_failure(
    llm_agent: LLMAgent, mock_provider: AsyncMock
) -> None:
    """
    Test handling of provider responses that fail parsing.
    Why: LLMs sometimes ignore formatting instructions. We need to ensure we return None
    (signaling failure) rather than crashing or returning garbage data.
    """
    mock_provider.complete.return_value = ("Just chatting, no tags", 10, 5)
    result = await llm_agent.get_move("fen", ["e4"], "white")
    assert result is None


@pytest.mark.asyncio
async def test_llm_agent_retry_move(llm_agent: LLMAgent, mock_provider: AsyncMock) -> None:
    """
    Test the retry logic which constructs a new prompt with error feedback.
    Why: The retry capability improves performance by allowing the LLM to self-correct.
    We need to verify that we are appending the correct error message to the history.
    """
    mock_provider.complete.return_value = ("<FinalMove>d4</FinalMove>", 15, 8)
    result = await llm_agent.retry_move(["e4"], "fen", ["e4", "d4"], "white")
    assert result is not None
    move, pt, ct = result
    assert move == "d4"
    assert pt == 15
    assert ct == 8
    # Check that messages include the failure
    messages = mock_provider.complete.call_args[0][0]
    assert any("e4 is illegal" in m["content"] for m in messages)
