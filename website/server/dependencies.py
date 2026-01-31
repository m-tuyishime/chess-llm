import os
from collections.abc import Generator

from chess_llm_eval.data.protocols import GameRepository
from chess_llm_eval.data.sqlite import SQLiteRepository


def get_repository() -> Generator[GameRepository, None, None]:
    """
    Dependency to provide a GameRepository instance.
    Defaults to looking for data/storage.db in the project root.
    For production/serverless deployment, set CHESS_DB_IMMUTABLE=true
    to use immutable mode (best for read-only filesystems like Vercel).
    """
    # Check if we're in immutable mode (production/serverless)
    immutable = os.getenv("CHESS_DB_IMMUTABLE", "false").lower() == "true"

    if immutable:
        # In immutable mode, resolve path relative to this file
        # This works regardless of the current working directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up two levels: website/server -> website -> root
        project_root = os.path.dirname(os.path.dirname(current_dir))
        db_path = os.path.join(project_root, "data", "storage.db")
    else:
        # Development mode: use env var or default relative path
        db_path = os.getenv("CHESS_DB_PATH", "data/storage.db")

    repository = SQLiteRepository(db_path=db_path, immutable=immutable)
    try:
        yield repository
    finally:
        repository.conn.close()
