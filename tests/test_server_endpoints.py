from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from chess_llm_eval.data.models import AgentData, Game, MoveRecord, Puzzle
from website.server.dependencies import get_repository
from website.server.main import app

# Dummy data for testing
MOCK_AGENT = AgentData(
    name="TestAgent", is_reasoning=False, is_random=False, rating=1600.0, rd=100.0, volatility=0.06
)

MOCK_PUZZLE = Puzzle(
    id="puzzle1",
    fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    moves="e2e4 e7e5",
    rating=1500,
    rating_deviation=50,
    themes="opening",
    type="mateIn2",
    popularity=100,
    nb_plays=10,
    game_url="http://example.com",
    opening_tags="King's Pawn",
)

MOCK_GAME = Game(
    id=1,
    puzzle_id="puzzle1",
    agent_name="TestAgent",
    failed=False,
    date=datetime.now(),
    moves=[
        MoveRecord(
            id=1,
            game_id=1,
            fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            expected_move="e2e4",
            actual_move="e2e4",
            is_illegal=False,
        )
    ],
)


class MockRepository:
    def get_leaderboard(self) -> list[Any]:
        ranking_cls = type(
            "Ranking",
            (),
            {
                "name": "TestAgent",
                "rating": 1600.0,
                "rd": 100.0,
                "win_rate": 50.0,
                "games_played": 10,
            },
        )
        return [ranking_cls()]

    def get_puzzles(self, limit: int | None = None) -> list[Puzzle]:
        return []

    def get_uncompleted_puzzles(self, agent_name: str, limit: int | None = None) -> list[Puzzle]:
        return []

    def save_puzzles(self, puzzles: list[Puzzle]) -> None:
        pass

    def save_agent(self, agent: AgentData) -> None:
        pass

    def get_all_agents(self) -> list[AgentData]:
        return []

    def create_game(self, puzzle_id: str, agent_name: str) -> int:
        return 1

    def update_game_result(self, game_id: int, failed: bool) -> None:
        pass

    def save_move(self, game_id: int, move: MoveRecord) -> None:
        pass

    def save_benchmark(self, game_id: int, rating: float, rd: float, volatility: float) -> None:
        pass

    def get_last_benchmark(self, agent_name: str) -> tuple[float, float, float] | None:
        return None

    def get_agent(self, name: str) -> AgentData | None:
        if name == "TestAgent":
            return MOCK_AGENT
        return None

    def get_game(self, game_id: int) -> Game | None:
        if game_id == 1:
            return MOCK_GAME
        return None

    def get_puzzle(self, puzzle_id: str) -> Puzzle | None:
        if puzzle_id == "puzzle1":
            return MOCK_PUZZLE
        return None

    def get_agent_games(self, agent_name: str) -> list[Game]:
        if agent_name == "TestAgent":
            return [MOCK_GAME]
        return []


@pytest.fixture
def client() -> TestClient:
    """
    Create a TestClient with mocked dependency.

    Why:
        To isolate the API implementation from the actual database for unit testing.
    """
    # Override dependency
    app.dependency_overrides[get_repository] = lambda: MockRepository()
    return TestClient(app)


def test_health_check(client: TestClient) -> None:
    """
    Test the health check endpoint.

    Why:
        To ensure the server is up and running.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_leaderboard(client: TestClient) -> None:
    """
    Test getting the agent leaderboard.

    Why:
        To verify that the leaderboard endpoint correctly returns agent rankings.
    """
    response = client.get("/api/leaderboard")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "TestAgent"
    assert data[0]["rating"] == 1600.0


def test_get_agent_detail(client: TestClient) -> None:
    """
    Test getting a specific agent's details.

    Why:
        To verify that agent details are correctly retrieved by name.
    """
    response = client.get("/api/agents/TestAgent")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "TestAgent"
    assert data["rating"] == 1600.0
    # Check that games list is present
    # (MockRepository.get_agent_games needs to represent this if main.py calls it)
    assert "games" in data


def test_get_agent_not_found(client: TestClient) -> None:
    """
    Test getting a non-existent agent returns 404.

    Why:
        To ensure proper error handling for invalid agent names.
    """
    response = client.get("/api/agents/Unknown")
    assert response.status_code == 404


def test_get_game(client: TestClient) -> None:
    """
    Test getting a specific game by ID.

    Why:
        To verify that game details including moves are correctly retrieved.
    """
    response = client.get("/api/games/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["agent_name"] == "TestAgent"
    assert len(data["moves"]) == 1
    assert data["moves"][0]["actual_move"] == "e2e4"


def test_get_game_not_found(client: TestClient) -> None:
    """
    Test getting a non-existent game returns 404.

    Why:
        To ensure proper error handling for invalid game IDs.
    """
    response = client.get("/api/games/999")
    assert response.status_code == 404


def test_get_puzzle(client: TestClient) -> None:
    """
    Test getting a specific puzzle by ID.

    Why:
        To verify that puzzle metadata is correctly retrieved.
    """
    response = client.get("/api/puzzles/puzzle1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "puzzle1"
    assert data["fen"] == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def test_get_puzzle_not_found(client: TestClient) -> None:
    """
    Test getting a non-existent puzzle returns 404.

    Why:
        To ensure proper error handling for invalid puzzle IDs.
    """
    response = client.get("/api/puzzles/unknown")
    assert response.status_code == 404
