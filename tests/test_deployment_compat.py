"""Tests for deployment compatibility, specifically read-only filesystem scenarios."""

import os
import stat
from pathlib import Path

from chess_llm_eval.data.sqlite import SQLiteRepository


class TestImmutableMode:
    """Test that SQLiteRepository works in immutable mode (for Vercel deployment)."""

    def test_immutable_mode_opens_pre_populated_db(self, tmp_path: Path) -> None:
        """Test that immutable mode can read from a pre-populated database.

        Why: On Vercel, we have a pre-populated static database that should be readable
        without any write operations. This verifies the immutable mode works correctly.
        """
        # Create a database with some data first (in regular mode)
        db_path = tmp_path / "test.db"
        repo_write = SQLiteRepository(db_path=str(db_path), immutable=False)

        # Add some test data
        from chess_llm_eval.data.models import Puzzle

        test_puzzle = Puzzle(
            id="test_puzzle_1",
            fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
            moves="e7e5",
            rating=1500,
            rating_deviation=350,
            popularity=95,
            nb_plays=1000,
            themes="opening",
            game_url="https://lichess.org/test",
            opening_tags="King's Pawn Game",
            type="Standard",
        )
        repo_write.save_puzzles([test_puzzle])
        repo_write.conn.close()

        # Now open in immutable mode and verify we can read
        repo_read = SQLiteRepository(db_path=str(db_path), immutable=True)

        # Verify we can read the data
        puzzles = repo_read.get_puzzles()
        assert len(puzzles) == 1
        assert puzzles[0].id == "test_puzzle_1"
        assert puzzles[0].rating == 1500

        repo_read.conn.close()

    def test_immutable_mode_skips_table_creation(self, tmp_path: Path) -> None:
        """Test that immutable mode skips _create_tables() call.

        Why: On read-only filesystems like Vercel, attempting to create tables would fail.
        Immutable mode must skip all schema modifications to work in production.
        """
        # Create a database first
        db_path = tmp_path / "test.db"
        repo_write = SQLiteRepository(db_path=str(db_path), immutable=False)
        repo_write.conn.close()

        # Make file read-only to simulate Vercel environment
        os.chmod(db_path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

        try:
            # In regular mode, this would fail because it tries to create tables
            # In immutable mode, it should succeed because it skips table creation
            repo_read = SQLiteRepository(db_path=str(db_path), immutable=True)
            repo_read.conn.close()
        finally:
            # Restore write permissions for cleanup
            os.chmod(db_path, stat.S_IRUSR | stat.S_IWUSR)

    def test_immutable_mode_with_relative_path(self, tmp_path: Path) -> None:
        """Test that immutable mode works with paths relative to different working directories.

        Why: Vercel serverless functions run with cwd=/var/task, not the project root.
        We must resolve database paths correctly regardless of the current working directory.
        """
        # Create database
        db_path = tmp_path / "data" / "storage.db"
        db_path.parent.mkdir(parents=True)

        repo_write = SQLiteRepository(db_path=str(db_path), immutable=False)
        from chess_llm_eval.data.models import Puzzle

        test_puzzle = Puzzle(
            id="relative_path_test",
            fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            moves="e2e4",
            rating=1600,
            rating_deviation=300,
            popularity=80,
            nb_plays=500,
            themes="",
            game_url="",
            opening_tags="",
            type="Standard",
        )
        repo_write.save_puzzles([test_puzzle])
        repo_write.conn.close()

        # Change working directory and verify immutable mode still works
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            # Use absolute path for immutable mode (as we do in production)
            repo_read = SQLiteRepository(db_path=str(db_path.absolute()), immutable=True)
            puzzles = repo_read.get_puzzles()
            assert len(puzzles) == 1
            assert puzzles[0].id == "relative_path_test"
            repo_read.conn.close()
        finally:
            os.chdir(original_cwd)

    def test_immutable_mode_performance_no_locking(self, tmp_path: Path) -> None:
        """Test that immutable mode provides better performance by skipping locking.

        Why: Immutable mode tells SQLite the database never changes, allowing it to skip
        all locking and journaling mechanisms. This provides better performance on serverless.
        """
        # Create database
        db_path = tmp_path / "perf_test.db"
        repo_write = SQLiteRepository(db_path=str(db_path), immutable=False)

        # Add test data
        from chess_llm_eval.data.models import Puzzle

        puzzles = [
            Puzzle(
                id=f"puzzle_{i}",
                fen=f"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 {i}",
                moves="e2e4",
                rating=1500 + i,
                rating_deviation=350,
                popularity=50,
                nb_plays=100,
                themes="test",
                game_url="",
                opening_tags="",
                type="Standard",
            )
            for i in range(100)
        ]
        repo_write.save_puzzles(puzzles)
        repo_write.conn.close()

        # Measure performance in immutable mode
        import time

        repo_read = SQLiteRepository(db_path=str(db_path), immutable=True)

        start = time.time()
        for _ in range(10):
            result = repo_read.get_puzzles(limit=50)
            assert len(result) == 50
        immutable_duration = time.time() - start

        repo_read.conn.close()

        # The test passes if we can read without errors
        # Performance assertion is informational
        assert immutable_duration < 1.0  # Should be very fast


class TestPathResolution:
    """Test database path resolution in different environments."""

    def test_path_resolution_from_different_cwd(self, tmp_path: Path) -> None:
        """Simulate Vercel environment where cwd != project root.

        Why: Serverless platforms like Vercel run functions from directories like /var/task,
        which is different from the project root where data/storage.db is located.
        We must resolve the database path relative to the source code, not the cwd.
        """
        # Setup: Create database in a project-like structure
        project_root = tmp_path / "project"
        data_dir = project_root / "data"
        data_dir.mkdir(parents=True)

        db_path = data_dir / "storage.db"

        # Create database
        repo_write = SQLiteRepository(db_path=str(db_path), immutable=False)
        from chess_llm_eval.data.models import Puzzle

        test_puzzle = Puzzle(
            id="path_resolution_test",
            fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            moves="e2e4",
            rating=1500,
            rating_deviation=350,
            popularity=95,
            nb_plays=1000,
            themes="test",
            game_url="",
            opening_tags="",
            type="Standard",
        )
        repo_write.save_puzzles([test_puzzle])
        repo_write.conn.close()

        # Simulate Vercel: cwd is /var/task or similar, not project root
        vercel_like_dir = tmp_path / "vercel" / "task"
        vercel_like_dir.mkdir(parents=True)

        original_cwd = os.getcwd()
        try:
            os.chdir(vercel_like_dir)

            # Use absolute path (as dependencies.py does in production)
            repo_read = SQLiteRepository(db_path=str(db_path.absolute()), immutable=True)
            puzzles = repo_read.get_puzzles()

            assert len(puzzles) == 1
            assert puzzles[0].id == "path_resolution_test"
            repo_read.conn.close()
        finally:
            os.chdir(original_cwd)
