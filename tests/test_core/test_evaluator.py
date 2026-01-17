from unittest.mock import MagicMock

import pytest

from chess_llm_eval.core.evaluator import Evaluator
from chess_llm_eval.data.models import Puzzle
from tests.conftest import MockRepository


@pytest.mark.asyncio
async def test_evaluator_evaluate_puzzle_success(
    mock_agent: MagicMock, sample_puzzle: Puzzle, mock_repo: MockRepository
) -> None:
    """
    Test the successful evaluation of a single puzzle.
    Why: Verifies the "happy path" where an agent provides a legal move. This ensures
    that the core evaluation loop, move parsing, and result recording function correctly.
    """
    # Solution 0: f3e5 (opponent), 1: c6e5 (model)
    mock_agent.get_move.return_value = ("Nxe5", 10, 5)

    evaluator = Evaluator(mock_agent, [sample_puzzle], mock_repo)
    result = await evaluator.evaluate_puzzle(sample_puzzle)

    assert result is not None
    game_id, (rating, rd, success) = result
    assert success is True
    assert game_id == 1
    assert rating == 1000
    assert rd == 100


@pytest.mark.asyncio
async def test_evaluator_evaluate_puzzle_illegal_move_retry(
    mock_agent: MagicMock, sample_puzzle: Puzzle, mock_repo: MockRepository
) -> None:
    """
    Test the retry mechanism when an agent makes an illegal move.
    Why: LLMs often make illegal moves. The system MUST give them a chance to correct
    themselves (up to the retry limit) to accurately measure their chess reasoning
    rather than just their syntax capabilities.
    """
    # First attempt illegal, second legal
    mock_agent.get_move.return_value = ("InvalidMove", 5, 5)
    mock_agent.retry_move.return_value = ("Nxe5", 5, 5)

    evaluator = Evaluator(mock_agent, [sample_puzzle], mock_repo)
    result = await evaluator.evaluate_puzzle(sample_puzzle)

    assert result is not None
    _, (_, _, success) = result
    assert success is True  # Recovered after retry

    # Verify both moves saved
    assert len(mock_repo.moves[1]) == 3  # 1 opponent + 1 illegal model + 1 legal model


def test_evaluator_update_agent_rating(mock_agent: MagicMock, mock_repo: MockRepository) -> None:
    """
    Test the Glicko-2 rating update logic.
    Why: The leaderboard is driven by these ratings. We need to verify that we are
    calling the Glicko-2 library correctly and persisting the updated ratings to
    the agent state.
    """
    evaluator = Evaluator(mock_agent, [], mock_repo)
    ratings = [1200.0, 1100.0]
    rds = [50.0, 60.0]
    outcomes = [True, False]

    new_r, new_rd, new_vol = evaluator.update_agent_rating(ratings, rds, outcomes)
    assert isinstance(new_r, float)
    assert isinstance(new_rd, float)
    assert isinstance(new_vol, float)
