"""
End-to-end integration tests for the full evaluation pipeline.

These tests validate the complete flow from puzzle loading through
agent evaluation to database storage, ensuring all components work
together correctly.
"""

import os
from pathlib import Path

import pytest

from chess_llm_eval.agents.llm import LLMAgent
from chess_llm_eval.core.evaluator import Evaluator
from chess_llm_eval.data.models import AgentData, Puzzle
from chess_llm_eval.data.sqlite import SQLiteRepository
from chess_llm_eval.providers.nim import NIMProvider

# Sample puzzles for testing
SAMPLE_PUZZLES = [
    Puzzle(
        id="e2e_tactic_1",
        fen="r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
        moves="f3e5 c6e5",  # Nxe5 Nxe5
        rating=1200,
        rating_deviation=100,
        themes="fork pin",
        type="tactic",
    ),
    Puzzle(
        id="e2e_endgame_1",
        fen="8/8/8/8/8/2k5/2p5/2K5 b - - 0 1",
        moves="c3d3 c1d1 c2c1q",  # King opposition and pawn promotion
        rating=1000,
        rating_deviation=80,
        themes="endgame pawn promotion",
        type="endgame",
    ),
    Puzzle(
        id="e2e_positional_1",
        fen="r1bqkbnr/pp1ppp1p/2n3p1/8/3NP3/8/PPP2PPP/RNBQKB1R w KQkq - 0 5",
        moves="d4c6 b7c6",  # Knight takes on c6
        rating=1100,
        rating_deviation=90,
        themes="positional material",
        type="positional",
    ),
]


@pytest.fixture
def test_db_path(tmp_path: Path) -> str:
    """Create a temporary database for testing."""
    db_path = str(tmp_path / "test_e2e.db")
    return db_path


@pytest.fixture
def repository(test_db_path: str) -> SQLiteRepository:
    """Create a fresh repository for testing."""
    repo = SQLiteRepository(test_db_path)
    repo.save_puzzles(SAMPLE_PUZZLES)
    return repo


@pytest.fixture
def nim_provider() -> NIMProvider | None:
    """Create NIM provider if API key is available."""
    if not os.getenv("NIM_API_KEY"):
        pytest.skip("NIM_API_KEY not set - skipping integration test")
    return NIMProvider()


def test_puzzle_repository_integration(repository: SQLiteRepository) -> None:
    """
    Test puzzle loading and repository integration.
    Why: Verifies that puzzles can be saved and retrieved from the database,
    and that uncompleted puzzle queries work correctly.
    """
    # Verify all puzzles were saved
    puzzles = repository.get_puzzles()
    assert len(puzzles) == 3
    assert puzzles[0].id == "e2e_tactic_1"
    assert puzzles[1].id == "e2e_endgame_1"
    assert puzzles[2].id == "e2e_positional_1"

    # Verify uncompleted puzzles query for new agent
    uncompleted = repository.get_uncompleted_puzzles("test_agent", limit=5)
    assert len(uncompleted) == 3


def test_agent_provider_integration(nim_provider: NIMProvider) -> None:
    """
    Test agent creation and configuration.
    Why: Ensures that LLMAgent can be properly instantiated with NIMProvider
    and that the configuration is correct.
    """
    agent = LLMAgent(
        provider=nim_provider,
        model_name="meta/llama-3.1-8b-instruct",
        is_reasoning=False,
    )

    assert agent.name == "meta/llama-3.1-8b-instruct"
    assert agent.model_name == "meta/llama-3.1-8b-instruct"
    assert agent.is_reasoning is False
    assert agent.provider == nim_provider


@pytest.mark.asyncio
@pytest.mark.integration
async def test_single_puzzle_evaluation(
    repository: SQLiteRepository, nim_provider: NIMProvider
) -> None:
    """
    Test evaluation of a single puzzle with real NIMProvider.
    Why: Validates the core evaluation loop with a real LLM provider,
    ensuring moves are saved, games are created, and results are updated.
    """
    agent = LLMAgent(
        provider=nim_provider,
        model_name="meta/llama-3.1-8b-instruct",
        is_reasoning=False,
    )

    # Save agent to repository
    repository.save_agent(
        AgentData(name=agent.name, is_reasoning=False, is_random=False)
    )

    evaluator = Evaluator(agent, [SAMPLE_PUZZLES[0]], repository)
    result = await evaluator.evaluate_puzzle(SAMPLE_PUZZLES[0])

    assert result is not None
    game_id, (rating, rd, success) = result
    assert game_id == 1
    assert rating == 1200
    assert rd == 100
    assert isinstance(success, bool)

    # Verify game was created
    cursor = repository.conn.execute("SELECT * FROM game WHERE id = ?", (game_id,))
    game = cursor.fetchone()
    assert game is not None
    assert game["puzzle_id"] == "e2e_tactic_1"
    assert game["agent_name"] == agent.name


@pytest.mark.asyncio
@pytest.mark.integration
async def test_multi_puzzle_evaluation(
    repository: SQLiteRepository, nim_provider: NIMProvider
) -> None:
    """
    Test concurrent evaluation of multiple puzzles.
    Why: Validates that evaluate_all() works correctly with concurrency,
    and that all results are properly saved to the repository.
    """
    agent = LLMAgent(
        provider=nim_provider,
        model_name="meta/llama-3.1-8b-instruct",
        is_reasoning=False,
    )

    repository.save_agent(
        AgentData(name=agent.name, is_reasoning=False, is_random=False)
    )

    evaluator = Evaluator(agent, SAMPLE_PUZZLES, repository)
    await evaluator.evaluate_all(max_concurrent=2)

    # Verify all games were created
    cursor = repository.conn.execute(
        "SELECT COUNT(*) as count FROM game WHERE agent_name = ?", (agent.name,)
    )
    count = cursor.fetchone()["count"]
    assert count == 3

    # Verify all puzzles have results
    cursor = repository.conn.execute(
        "SELECT * FROM game WHERE agent_name = ?", (agent.name,)
    )
    games = cursor.fetchall()
    assert len(games) == 3


@pytest.mark.asyncio
@pytest.mark.integration
async def test_rating_update_flow(
    repository: SQLiteRepository, nim_provider: NIMProvider
) -> None:
    """
    Test Glicko-2 rating updates after puzzle completion.
    Why: Verifies that benchmark records are created and agent rating
    cache is updated correctly after each evaluation.
    """
    agent = LLMAgent(
        provider=nim_provider,
        model_name="meta/llama-3.1-8b-instruct",
        is_reasoning=False,
    )

    repository.save_agent(
        AgentData(name=agent.name, is_reasoning=False, is_random=False)
    )

    evaluator = Evaluator(agent, [SAMPLE_PUZZLES[0]], repository)
    result = await evaluator.evaluate_puzzle(SAMPLE_PUZZLES[0])

    assert result is not None
    game_id, _ = result

    # Verify benchmark was created
    cursor = repository.conn.execute(
        "SELECT * FROM benchmark WHERE game_id = ?", (game_id,)
    )
    benchmark = cursor.fetchone()
    assert benchmark is not None
    assert benchmark["agent_rating"] is not None
    assert benchmark["agent_deviation"] is not None
    assert benchmark["agent_volatility"] is not None

    # Verify agent cache was updated
    agent_data = repository.get_agent(agent.name)
    assert agent_data is not None
    assert agent_data.rating != 1500.0  # Should have changed from default


@pytest.mark.asyncio
@pytest.mark.integration
async def test_illegal_move_handling_e2e(
    repository: SQLiteRepository, nim_provider: NIMProvider
) -> None:
    """
    Test illegal move handling in the full pipeline.
    Why: LLMs often make illegal moves. We need to verify that the retry
    mechanism works end-to-end and all attempts are logged.
    """
    agent = LLMAgent(
        provider=nim_provider,
        model_name="meta/llama-3.1-8b-instruct",
        is_reasoning=False,
    )

    repository.save_agent(
        AgentData(name=agent.name, is_reasoning=False, is_random=False)
    )

    evaluator = Evaluator(agent, [SAMPLE_PUZZLES[0]], repository)
    result = await evaluator.evaluate_puzzle(SAMPLE_PUZZLES[0])

    assert result is not None
    game_id, _ = result

    # Check if any illegal moves were made
    cursor = repository.conn.execute(
        "SELECT * FROM move WHERE game_id = ? AND illegal_move = 1", (game_id,)
    )
    illegal_moves = cursor.fetchall()

    # Whether illegal moves occurred or not, verify all moves were logged
    cursor = repository.conn.execute("SELECT COUNT(*) as count FROM move WHERE game_id = ?", (game_id,))
    move_count = cursor.fetchone()["count"]
    assert move_count > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_three_agents_three_puzzles(
    repository: SQLiteRepository, nim_provider: NIMProvider
) -> None:
    """
    CRITICAL TEST: Run 3 NIM models on 3 puzzles (Roadmap 1.6 requirement).
    Why: This validates the complete pipeline with multiple agents and puzzles,
    which is the core requirement of Roadmap 1.6.
    """
    models = [
        "meta/llama-3.1-8b-instruct",
        "meta/llama-3.1-70b-instruct",
        "mistralai/mixtral-8x7b-instruct-v0.1",
    ]

    results = []

    for model_name in models:
        agent = LLMAgent(
            provider=nim_provider,
            model_name=model_name,
            is_reasoning=False,
        )

        repository.save_agent(
            AgentData(name=agent.name, is_reasoning=False, is_random=False)
        )

        evaluator = Evaluator(agent, SAMPLE_PUZZLES, repository)
        await evaluator.evaluate_all(max_concurrent=2)

        results.append(agent.name)

    # Verify all 3 agents completed
    assert len(results) == 3

    # Verify total games created: 3 agents × 3 puzzles = 9 games
    cursor = repository.conn.execute("SELECT COUNT(*) as count FROM game")
    total_games = cursor.fetchone()["count"]
    assert total_games == 9

    # Verify each agent has 3 games
    for model_name in models:
        cursor = repository.conn.execute(
            "SELECT COUNT(*) as count FROM game WHERE agent_name = ?", (model_name,)
        )
        agent_games = cursor.fetchone()["count"]
        assert agent_games == 3

    # Verify benchmarks exist for all games
    cursor = repository.conn.execute("SELECT COUNT(*) as count FROM benchmark")
    total_benchmarks = cursor.fetchone()["count"]
    assert total_benchmarks == 9

    # Verify all agents have updated ratings
    for model_name in models:
        agent_data = repository.get_agent(model_name)
        assert agent_data is not None
        assert agent_data.rating != 1500.0  # Should have changed from default
        assert agent_data.rd < 350.0  # RD should have decreased after evaluations
