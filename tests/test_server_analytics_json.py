"""Integration tests for analytics endpoints using JSONRepository."""

import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from chess_llm_eval.data.json_repo import JSONRepository
from chess_llm_eval.schemas import AgentPuzzleOutcomeResponse, AnalyticsResponse
from website.server.dependencies import get_repository
from website.server.main import app


def ensure_json_data() -> None:
    """Ensure data.json exists, generate it if needed.

    Why:
        The JSONRepository requires data.json to exist. This mirrors the
        Vercel build step which generates the file from storage.db.
    """
    if not Path("data.json").exists():
        subprocess.run([sys.executable, "build.py"], check=True)


@pytest.fixture(scope="module", autouse=True)
def _generate_json_data() -> None:
    """Generate data.json before running tests in this module.

    Why:
        Prevents CI failures if data.json is missing and ensures the
        JSONRepository mirrors production behavior.
    """
    ensure_json_data()


@pytest.fixture()
def client() -> TestClient:
    """Create a TestClient using JSONRepository.

    Why:
        Ensures analytics endpoints work with JSON-backed data as in Vercel.
    """
    app.dependency_overrides[get_repository] = lambda: JSONRepository("data.json")
    return TestClient(app)


def test_analytics_endpoint_json_repo(client: TestClient) -> None:
    """Analytics endpoint should return 200 with JSONRepository.

    Why:
        The agent detail page depends on /api/analytics; failures here break UI.
    """
    response = client.get("/api/analytics")
    assert response.status_code == 200
    data = response.json()
    analytics = AnalyticsResponse.model_validate(data)
    assert isinstance(analytics.rating_trends, list)
    assert isinstance(analytics.puzzle_outcomes, list)
    assert "weighted_puzzle_rating" in data
    assert "weighted_puzzle_deviation" in data
    assert data["weighted_puzzle_rating"] is None or isinstance(
        data["weighted_puzzle_rating"], (int, float)
    )
    assert data["weighted_puzzle_deviation"] is None or isinstance(
        data["weighted_puzzle_deviation"], (int, float)
    )


def test_agent_analytics_endpoint_json_repo(client: TestClient) -> None:
    """Agent analytics should work with URL-encoded names.

    Why:
        Real agent names include slashes and must round-trip in production.
    """
    response = client.get("/api/analytics/agents/meta%2Fllama-3.1-405b-instruct")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for item in data:
        AgentPuzzleOutcomeResponse.model_validate(item)
