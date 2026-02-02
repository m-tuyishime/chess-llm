"""Parity tests to ensure JSON and SQLite API outputs match exactly."""

import subprocess
import sys
from collections.abc import Generator
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from chess_llm_eval.data.json_repo import JSONRepository
from chess_llm_eval.data.sqlite import SQLiteRepository
from website.server.dependencies import get_repository
from website.server.main import app


def ensure_json_data() -> None:
    """Ensure data.json exists, generate it if needed."""
    if not Path("data.json").exists():
        subprocess.run([sys.executable, "build.py"], check=True)


@pytest.fixture(scope="module", autouse=True)
def _generate_json_data() -> None:
    ensure_json_data()


@pytest.fixture(scope="module")
def sqlite_repo() -> SQLiteRepository:
    return SQLiteRepository(db_path="data/storage.db", immutable=True)


@pytest.fixture(scope="module")
def json_repo() -> JSONRepository:
    return JSONRepository(json_path="data.json")


def _client_for_repo(repo: object) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_repository] = lambda: repo
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_repository, None)


@pytest.fixture()
def sqlite_client(sqlite_repo: SQLiteRepository) -> Generator[TestClient, None, None]:
    yield from _client_for_repo(sqlite_repo)


@pytest.fixture()
def json_client(json_repo: JSONRepository) -> Generator[TestClient, None, None]:
    yield from _client_for_repo(json_repo)


def _pick_agent_with_games(sqlite_repo: SQLiteRepository) -> str:
    for agent in sqlite_repo.get_all_agents():
        if sqlite_repo.get_agent_games(agent.name):
            return agent.name
    pytest.skip("No agents with games available for parity tests")


def _get_json(client: TestClient, path: str) -> object:
    response = client.get(path)
    assert response.status_code == 200
    return response.json()


def test_leaderboard_parity(sqlite_client: TestClient, json_client: TestClient) -> None:
    """Leaderboard outputs should match exactly.

    Why: The UI relies on stable rankings across storage backends.
    """
    sqlite_data = _get_json(sqlite_client, "/api/leaderboard")
    json_data = _get_json(json_client, "/api/leaderboard")
    assert sqlite_data == json_data


def test_analytics_parity(sqlite_client: TestClient, json_client: TestClient) -> None:
    """Analytics payloads should match exactly.

    Why: Charts and aggregates must be consistent between SQLite and JSON.
    """
    sqlite_data = _get_json(sqlite_client, "/api/analytics")
    json_data = _get_json(json_client, "/api/analytics")
    assert sqlite_data == json_data


def test_agent_detail_parity(
    sqlite_repo: SQLiteRepository,
    sqlite_client: TestClient,
    json_client: TestClient,
) -> None:
    """Agent detail responses should match exactly.

    Why: The agent details page must render the same game summaries in production.
    """
    agent_name = _pick_agent_with_games(sqlite_repo)
    encoded = quote(agent_name, safe="")
    sqlite_data = _get_json(sqlite_client, f"/api/agents/{encoded}")
    json_data = _get_json(json_client, f"/api/agents/{encoded}")
    assert sqlite_data == json_data


def test_game_detail_parity(
    sqlite_repo: SQLiteRepository,
    sqlite_client: TestClient,
    json_client: TestClient,
) -> None:
    """Game detail responses should match exactly.

    Why: Game payloads back the analysis view and must not diverge.
    """
    row = sqlite_repo.conn.execute("SELECT id FROM game ORDER BY id LIMIT 1").fetchone()
    if not row:
        pytest.skip("No games available for parity tests")
    game_id = row["id"]
    sqlite_data = _get_json(sqlite_client, f"/api/games/{game_id}")
    json_data = _get_json(json_client, f"/api/games/{game_id}")
    assert sqlite_data == json_data


def test_puzzle_detail_parity(
    sqlite_repo: SQLiteRepository,
    sqlite_client: TestClient,
    json_client: TestClient,
) -> None:
    """Puzzle detail responses should match exactly.

    Why: The puzzle detail panel must be consistent across backends.
    """
    puzzles = sqlite_repo.get_puzzles(limit=1)
    if not puzzles:
        pytest.skip("No puzzles available for parity tests")
    puzzle_id = puzzles[0].id
    sqlite_data = _get_json(sqlite_client, f"/api/puzzles/{puzzle_id}")
    json_data = _get_json(json_client, f"/api/puzzles/{puzzle_id}")
    assert sqlite_data == json_data
