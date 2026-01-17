import os
from collections.abc import Generator

from chess_llm_eval.data.protocols import GameRepository
from chess_llm_eval.data.sqlite import SQLiteRepository


def get_repository() -> Generator[GameRepository, None, None]:
    """
    Dependency to provide a GameRepository instance.
    Defaults to looking for data/storage.db in the project root.
    """
    # Assuming the server is run from the project root or relative path handling
    # We'll default to "data/storage.db" relative to where it was run,
    # or look for an env var.
    db_path = os.getenv("CHESS_DB_PATH", "data/storage.db")

    # Ensure directory exists if we were to write, but here we just read mostly.
    # SQLiteRepository handles table creation if it doesn't exist.

    repository = SQLiteRepository(db_path=db_path)
    try:
        yield repository
    finally:
        # SQLiteRepository uses a persistent connection in current impl,
        # but if we needed to close it, we would do it here.
        # Current SQLiteRepository implementation holds self.conn.
        # We can explicitly close if meaningful, but typically
        # for SQLite in FastAPI with threading, a new connection per request
        # or a singleton is chosen.
        # Given SQLiteRepository opens connection in __init__,
        # creating a new one per request is safe but might be slightly overhead
        # due to file opening.
        # For this scale, it's fine.
        repository.conn.close()
