from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# Load .env file for integration tests
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

from chess_llm_eval.agents.base import Agent  # noqa: E402
from chess_llm_eval.data.models import (  # noqa: E402
    AgentData,
    AgentRanking,
    Game,
    MoveRecord,
    Puzzle,
)
from chess_llm_eval.data.protocols import GameRepository  # noqa: E402
from chess_llm_eval.providers.base import LLMProvider  # noqa: E402


def pytest_runtest_setup(item: pytest.Item) -> None:
    """
    Hook to enforce docstring standards on all test functions.
    Fails the test if it lacks a docstring or a 'Why:' justification.
    """
    if isinstance(item, pytest.Function):
        doc = item.obj.__doc__
        if not doc:
            pytest.fail(f"Test '{item.name}' is missing a docstring.")

        if "Why:" not in doc:
            pytest.fail(
                f"Test '{item.name}' docstring missing 'Why:' justification section.\n"
                f"Current docstring:\n{doc}"
            )


class MockRepository(GameRepository):
    def __init__(self) -> None:
        self.games: dict[int, dict[str, Any]] = {}
        self.moves: dict[int, list[MoveRecord]] = {}
        self.agents: dict[str, AgentData] = {}
        self.puzzles: list[Puzzle] = []
        self.benchmarks: list[dict[str, Any]] = []

    def get_puzzles(self, limit: int | None = None) -> list[Puzzle]:
        return self.puzzles[:limit] if limit else self.puzzles

    def get_uncompleted_puzzles(self, agent_name: str, limit: int | None = None) -> list[Puzzle]:
        # Very simple mock: return all puzzles
        return self.puzzles[:limit] if limit else self.puzzles

    def save_puzzles(self, puzzles: list[Puzzle]) -> None:
        self.puzzles.extend(puzzles)

    def get_agent(self, name: str) -> AgentData | None:
        return self.agents.get(name)

    def save_agent(self, agent: AgentData) -> None:
        self.agents[agent.name] = agent

    def get_all_agents(self) -> list[AgentData]:
        return list(self.agents.values())

    def create_game(self, puzzle_id: str, agent_name: str) -> int:
        game_id = len(self.games) + 1
        self.games[game_id] = {"puzzle_id": puzzle_id, "agent_name": agent_name, "failed": False}
        return game_id

    def update_game_result(self, game_id: int, failed: bool) -> None:
        if game_id in self.games:
            self.games[game_id]["failed"] = failed

    def save_move(self, game_id: int, move: MoveRecord) -> None:
        if game_id not in self.moves:
            self.moves[game_id] = []
        self.moves[game_id].append(move)

    def save_benchmark(self, game_id: int, rating: float, rd: float, volatility: float) -> None:
        self.benchmarks.append(
            {"game_id": game_id, "rating": rating, "rd": rd, "volatility": volatility}
        )

    def get_last_benchmark(self, agent_name: str) -> tuple[float, float, float] | None:
        return (1500.0, 350.0, 0.06)

    def get_leaderboard(self) -> list[AgentRanking]:
        return []

    def get_agent_games(self, agent_name: str) -> list[Game]:
        return []

    def get_game(self, game_id: int) -> Game | None:
        return None

    def get_puzzle(self, puzzle_id: str) -> Puzzle | None:
        return None


@pytest.fixture
def mock_repo() -> MockRepository:
    return MockRepository()


@pytest.fixture
def sample_puzzle() -> Puzzle:
    return Puzzle(
        id="test_puzzle_1",
        fen="r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
        moves="f3e5 c6e5",
        rating=1000,
        rating_deviation=100,
        themes="test",
        type="tactic",
    )


@pytest.fixture
def mock_llm_provider() -> MagicMock:
    provider = MagicMock(spec=LLMProvider)
    provider.complete.return_value = ("e4e5", 10, 5)
    return provider


class ConcreteAgent(Agent):
    async def get_move(self, fen: str, legal_moves: list[str], color: str) -> tuple[str, int, int]:
        return ("e4e5", 10, 5)

    async def retry_move(
        self, failed_moves: list[str], fen: str, legal_moves: list[str], color: str
    ) -> tuple[str, int, int]:
        return ("e4e5", 10, 5)


@pytest.fixture
def sample_agent() -> ConcreteAgent:
    return ConcreteAgent(model_name="test_agent")


@pytest.fixture
def mock_agent() -> MagicMock:
    agent = MagicMock(spec=Agent)
    agent.name = "test_mock_agent"
    agent.get_move = AsyncMock()
    agent.retry_move = AsyncMock()
    # Default rating values
    agent.rating = 1500.0
    agent.rd = 350.0
    agent.volatility = 0.06
    return agent
