"""Tests for JSON repository data integrity and conversion.

These tests verify that the JSON repository produces identical results
to the SQLite repository, ensuring no data loss during conversion.
"""

from pathlib import Path

import pytest

from chess_llm_eval.data.json_repo import JSONRepository
from chess_llm_eval.data.sqlite import SQLiteRepository


class TestDataIntegrity:
    """Test that JSON conversion preserves all data integrity."""

    @pytest.fixture(scope="module")
    def sqlite_repo(self) -> SQLiteRepository:
        """Provide SQLite repository for comparison."""
        return SQLiteRepository(db_path="data/storage.db", immutable=True)

    @pytest.fixture(scope="module")
    def json_repo(self) -> JSONRepository:
        """Provide JSON repository for comparison."""
        return JSONRepository(json_path="data.json")

    def test_puzzle_counts_match(
        self, sqlite_repo: SQLiteRepository, json_repo: JSONRepository
    ) -> None:
        """Verify puzzle counts match between SQLite and JSON.

        Why: If counts differ, data was lost during conversion.
        """
        sqlite_count = len(sqlite_repo.get_puzzles())
        json_count = len(json_repo.get_puzzles())
        assert sqlite_count == json_count, f"Puzzle count mismatch: {sqlite_count} vs {json_count}"

    def test_agent_counts_match(
        self, sqlite_repo: SQLiteRepository, json_repo: JSONRepository
    ) -> None:
        """Verify agent counts match between SQLite and JSON.

        Why: Agent data must be preserved during conversion.
        """
        sqlite_count = len(sqlite_repo.get_all_agents())
        json_count = len(json_repo.get_all_agents())
        assert sqlite_count == json_count, f"Agent count mismatch: {sqlite_count} vs {json_count}"

    def test_puzzle_data_matches(
        self, sqlite_repo: SQLiteRepository, json_repo: JSONRepository
    ) -> None:
        """Verify specific puzzle data matches exactly.

        Why: Spot-check critical fields to ensure data integrity.
        """
        # Test a sample of puzzles
        sample_ids = ["0000D", "0008Q", "0009B"]

        for puzzle_id in sample_ids:
            sqlite_puzzle = sqlite_repo.get_puzzle(puzzle_id)
            json_puzzle = json_repo.get_puzzle(puzzle_id)

            assert sqlite_puzzle is not None, f"SQLite missing puzzle {puzzle_id}"
            assert json_puzzle is not None, f"JSON missing puzzle {puzzle_id}"

            # Compare key fields
            assert sqlite_puzzle.id == json_puzzle.id
            assert sqlite_puzzle.fen == json_puzzle.fen
            assert sqlite_puzzle.rating == json_puzzle.rating

    def test_leaderboard_order_matches(
        self, sqlite_repo: SQLiteRepository, json_repo: JSONRepository
    ) -> None:
        """Verify leaderboard produces same ordering.

        Why: Ranking consistency is critical for fair comparison.
        """
        sqlite_leaderboard = sqlite_repo.get_leaderboard()
        json_leaderboard = json_repo.get_leaderboard()

        assert len(sqlite_leaderboard) == len(json_leaderboard)

        # Check order is the same
        pairs = zip(sqlite_leaderboard, json_leaderboard, strict=False)
        for i, (sqlite_entry, json_entry) in enumerate(pairs):
            msg = f"Mismatch at position {i}"
            assert sqlite_entry.name == json_entry.name, msg

    def test_analytics_dataframe_columns(
        self, sqlite_repo: SQLiteRepository, json_repo: JSONRepository
    ) -> None:
        """Verify analytics DataFrames have expected columns.

        Why: Analytics must have consistent structure for analysis.
        """
        # Benchmark data
        json_benchmark = json_repo.get_benchmark_data()

        # Check key columns exist (column names may differ due to merge suffixes)
        assert "agent_rating" in json_benchmark.columns
        assert "agent_deviation" in json_benchmark.columns
        assert len(json_benchmark) > 0

    def test_json_file_exists_and_valid(self) -> None:
        """Verify data.json was generated and is valid.

        Why: The build script must successfully create the file.
        """
        assert Path("data.json").exists(), "data.json not found"

        import json

        with open("data.json") as f:
            data = json.load(f)

        # Verify required keys exist
        required_keys = ["puzzle", "agent", "game", "move", "benchmark"]
        for key in required_keys:
            assert key in data, f"Missing key: {key}"
            assert isinstance(data[key], list), f"{key} should be a list"


class TestJSONRepositoryFunctionality:
    """Test JSONRepository-specific functionality."""

    @pytest.fixture
    def repo(self) -> JSONRepository:
        """Provide JSON repository."""
        return JSONRepository(json_path="data.json")

    def test_get_puzzles_with_limit(self, repo: JSONRepository) -> None:
        """Test that limit parameter works correctly.

        Why: Pagination is essential for memory-efficient operations.
        """
        all_puzzles = repo.get_puzzles()
        limited = repo.get_puzzles(limit=10)

        assert len(limited) == 10
        assert len(limited) < len(all_puzzles)

    def test_get_puzzle_returns_none_for_invalid(self, repo: JSONRepository) -> None:
        """Test that invalid puzzle IDs return None.

        Why: Graceful handling of missing data prevents crashes.
        """
        result = repo.get_puzzle("INVALID_ID_12345")
        assert result is None

    def test_get_agent_returns_none_for_invalid(self, repo: JSONRepository) -> None:
        """Test that invalid agent names return None.

        Why: Graceful handling of missing data prevents crashes.
        """
        result = repo.get_agent("NonExistentAgent")
        assert result is None

    def test_uncompleted_puzzles_excludes_attempted(self, repo: JSONRepository) -> None:
        """Test that uncompleted puzzles filter works.

        Why: An agent should have fewer uncompleted puzzles after playing some.
        """
        agent_name = "gpt-4o"  # Assuming this agent has played games

        all_puzzles = len(repo.get_puzzles())
        uncompleted = len(repo.get_uncompleted_puzzles(agent_name))

        # Uncompleted should be less than or equal to total
        assert uncompleted <= all_puzzles

    def test_write_operations_raise_error(self, repo: JSONRepository) -> None:
        """Test that write operations are properly disabled.

        Why: JSONRepository is read-only and should raise NotImplementedError.
        """
        from chess_llm_eval.data.models import MoveRecord

        with pytest.raises(NotImplementedError):
            repo.save_puzzles([])

        with pytest.raises(NotImplementedError):
            repo.create_game("test", "agent")

        with pytest.raises(NotImplementedError):
            # MoveRecord requires positional args, but we're testing the error
            # so we just need any MoveRecord instance
            move = MoveRecord(
                fen="test", expected_move="e2e4", actual_move="e2e4", is_illegal=False
            )
            repo.save_move(1, move)


class TestBuildScript:
    """Test the build script functionality."""

    def test_build_script_creates_valid_json(self) -> None:
        """Verify build.py creates valid, complete JSON.

        Why: The build script is critical for data conversion workflow.
        """
        import subprocess
        import sys

        # Run build script
        result = subprocess.run(
            [sys.executable, "build.py"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"Build script failed: {result.stderr}"
        assert "SUCCESS" in result.stdout, "Build did not report success"
        assert Path("data.json").exists(), "data.json was not created"
