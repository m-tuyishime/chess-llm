import os
from collections.abc import Generator
from pathlib import Path

from chess_llm_eval.data.json_repo import JSONRepository
from chess_llm_eval.data.protocols import GameRepository
from chess_llm_eval.data.sqlite import SQLiteRepository


def get_repository() -> Generator[GameRepository, None, None]:
    """
    Dependency to provide a GameRepository instance.

    Supports two modes:
    1. **SQLite mode** (default for development): Uses SQLite database
    2. **JSON mode** (for Vercel production): Uses JSON file for serverless deployment

    Environment variables:
    - CHESS_REPO_TYPE: Set to "json" for JSON mode, "sqlite" for SQLite mode (default: sqlite)
    - CHESS_DB_PATH: Path to SQLite database (default: data/storage.db)
    - CHESS_JSON_PATH: Path to JSON data file (default: data.json)
    - CHESS_DB_IMMUTABLE: For SQLite mode, use immutable read-only mode (default: false)

    For Vercel deployment, set CHESS_REPO_TYPE=json and include data.json in the bundle.
    """
    repo_type = os.getenv("CHESS_REPO_TYPE", "sqlite").lower()

    if repo_type == "json":
        # JSON mode - for Vercel serverless deployment
        json_path = os.getenv("CHESS_JSON_PATH", "data.json")

        # In serverless environment, resolve from project root
        if not Path(json_path).is_absolute():
            # Try to find relative to current file (website/server/dependencies.py)
            current_dir = Path(__file__).parent
            # Go up to project root: website/server -> website -> root
            project_root = current_dir.parent.parent
            json_path_full = project_root / json_path

            # Fall back to direct path if not found
            if not json_path_full.exists():
                json_path_full = Path(json_path)
        else:
            json_path_full = Path(json_path)

        repository: GameRepository = JSONRepository(str(json_path_full))
        try:
            yield repository
        finally:
            # JSONRepository doesn't need explicit cleanup
            pass

    else:
        # SQLite mode - for local development
        immutable = os.getenv("CHESS_DB_IMMUTABLE", "false").lower() == "true"

        if immutable:
            # In immutable mode, resolve path relative to this file
            current_dir = Path(__file__).parent
            # Go up two levels: website/server -> website -> root
            project_root = current_dir.parent.parent
            db_path = project_root / "data" / "storage.db"
        else:
            # Development mode: use env var or default relative path
            db_path = Path(os.getenv("CHESS_DB_PATH", "data/storage.db"))

        repository = SQLiteRepository(db_path=str(db_path), immutable=immutable)
        try:
            yield repository
        finally:
            repository.conn.close()
