import json
import logging
from pathlib import Path

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
                    rating=p_data.get("rating", 1500),
                    rating_deviation=p_data.get("rating_deviation", 350),
                    popularity=p_data.get("popularity", 0),
                    nb_plays=p_data.get("nb_plays", 0),
                    themes=p_data.get("themes", ""),
                    game_url=p_data.get("game_url", ""),
                    opening_tags=p_data.get("opening_tags", ""),
                    type=p_data.get("type", "unknown"),
                )
            )

        self.repo.save_puzzles(puzzles)
        logger.info(f"Imported {len(puzzles)} puzzles from {input_path}")
