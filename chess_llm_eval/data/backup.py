import json
import logging
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from chess_llm_eval.data.models import Puzzle
from chess_llm_eval.data.sqlite import SQLiteRepository

logger = logging.getLogger(__name__)


class PuzzleBackup:
    """Helper class to backup and restore puzzles from JSON."""

    def __init__(self, db_path: str = "data/storage.db") -> None:
        self.db_path = db_path
        self.repo = SQLiteRepository(db_path)

    def export_puzzles_to_json(self, json_path: str = "data/puzzles.json") -> None:
        """Exports all puzzles from the database to a JSON file."""
        puzzles = self.repo.get_puzzles()

        # Convert Puzzle objects to dictionaries
        puzzles_data = []
        for p in puzzles:
            puzzles_data.append(
                {
                    "id": p.id,
                    "fen": p.fen,
                    "moves": p.moves,
                    "rating": p.rating,
                    "rating_deviation": p.rating_deviation,
                    "popularity": p.popularity,
                    "nb_plays": p.nb_plays,
                    "themes": p.themes,
                    "game_url": p.game_url,
                    "opening_tags": p.opening_tags,
                    "type": p.type,
                }
            )

        output_path = Path(json_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(puzzles_data, f, indent=2)

        logger.info(f"Exported {len(puzzles)} puzzles to {output_path}")

    def import_puzzles_from_json(self, json_path: str = "data/puzzles.json") -> None:
        """Imports puzzles from a JSON file into the database."""
        input_path = Path(json_path)
        if not input_path.exists():
            logger.warning(f"JSON file not found: {input_path}")
            return

        with open(input_path, encoding="utf-8") as f:
            puzzles_data = json.load(f)

        puzzles = []
        for p_data in puzzles_data:
            puzzles.append(
                Puzzle(
                    id=p_data.get("id", ""),
                    fen=p_data.get("fen", ""),
                    moves=p_data.get("moves", ""),
                    rating=p_data.get("rating") or 1500,
                    rating_deviation=p_data.get("rating_deviation") or 350,
                    popularity=p_data.get("popularity") or 0,
                    nb_plays=p_data.get("nb_plays") or 0,
                    themes=p_data.get("themes") or "",
                    game_url=p_data.get("game_url") or "",
                    opening_tags=p_data.get("opening_tags") or "",
                    type=p_data.get("type") or "unknown",
                )
            )

        self.repo.save_puzzles(puzzles)
        logger.info(f"Imported {len(puzzles)} puzzles from {input_path}")


class FullDatabaseBackup:
    """Helper class to backup and restore the entire database."""

    def __init__(self, db_path: str = "data/storage.db") -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def export_all_to_json(self, json_path: str | None = None) -> str:
        """Exports all tables to a single JSON file."""
        if not json_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_path = f"data/backups/full_backup_{timestamp}.json"

        output_path = Path(json_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data: dict[str, Any] = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "db_path": str(self.db_path),
            },
            "tables": {},
        }

        tables = ["puzzle", "agent", "game", "move", "benchmark"]
        for table in tables:
            cursor = self.conn.execute(f"SELECT * FROM {table}")
            data["tables"][table] = [dict(row) for row in cursor.fetchall()]

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Full JSON backup created at {output_path}")
        return str(output_path)

    def sqlite_dump(self, dump_path: str | None = None) -> str:
        """Creates a SQL dump of the database."""
        if not dump_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dump_path = f"data/backups/db_dump_{timestamp}.sql"

        output_path = Path(dump_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            # Use sqlite3 CLI if available for a clean dump
            try:
                subprocess.run(
                    ["sqlite3", self.db_path, ".dump"],
                    stdout=f,
                    check=True,
                    capture_output=False,
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Fallback to internal iteration if sqlite3 CLI is missing
                logger.warning("sqlite3 CLI not found, using internal dump fallback")
                for line in self.conn.iterdump():
                    f.write(f"{line}\n")

        logger.info(f"SQLite dump created at {output_path}")
        return str(output_path)

    def restore_from_json(self, json_path: str) -> None:
        """Restores the database from a JSON backup file."""
        input_path = Path(json_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Backup file not found: {input_path}")

        with open(input_path, encoding="utf-8") as f:
            data = json.load(f)

        cursor = self.conn.cursor()

        # Disable foreign keys during restore
        cursor.execute("PRAGMA foreign_keys = OFF")

        try:
            for table_name, rows in data["tables"].items():
                if not rows:
                    continue

                cursor.execute(f"DELETE FROM {table_name}")
                columns = rows[0].keys()
                placeholders = ", ".join(["?"] * len(columns))
                query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

                values = [tuple(row[col] for col in columns) for row in rows]
                cursor.executemany(query, values)
                logger.info(f"Restored {len(rows)} rows to {table_name}")

            self.conn.commit()
        finally:
            cursor.execute("PRAGMA foreign_keys = ON")

        logger.info("Database restoration complete")
