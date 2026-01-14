import logging
import os
from typing import Any

import pandas as pd

from chess_llm_eval.data.models import Puzzle
from chess_llm_eval.data.sqlite import SQLiteRepository

logger = logging.getLogger(__name__)


class PuzzleSeeder:
    """Helper class to seed the database with puzzles from CSV files."""

    def __init__(self, repository: SQLiteRepository) -> None:
        self.repo = repository

    def _get_shuffled_puzzles_from_csv(self, csv_path: str) -> pd.DataFrame:
        if not os.path.exists(csv_path):
            logger.warning(f"CSV file not found: {csv_path}")
            return pd.DataFrame()
        df = pd.read_csv(csv_path)
        return df.sample(frac=1).reset_index(drop=True)

    def _get_val(self, row: pd.Series, names: list[str], default: Any = None) -> Any:
        for name in names:
            if name in row:
                return row[name]
        return default

    def seed_from_standard_paths(self) -> None:
        """
        Seeds the database using the standard tactic, strategy, and endgame CSVs
        if they exist in the 'data' directory.
        """
        tactic_df = self._get_shuffled_puzzles_from_csv("data/TacticDB.csv")
        strategy_df = self._get_shuffled_puzzles_from_csv("data/StrategicDB.csv")
        endgame_df = self._get_shuffled_puzzles_from_csv("data/EndgameDB.csv")

        if tactic_df.empty and strategy_df.empty and endgame_df.empty:
            logger.info("No puzzle CSVs found to seed.")
            return

        # Interleave puzzles to ensure balanced categories if limited
        num_cycles: float | int = min(
            len(tactic_df) if not tactic_df.empty else float("inf"),
            len(strategy_df) if not strategy_df.empty else float("inf"),
            len(endgame_df) if not endgame_df.empty else float("inf"),
        )

        if num_cycles == float("inf"):
            # Just take what we have
            all_puzzles = pd.concat([tactic_df, strategy_df, endgame_df])
        else:
            combined_rows = []
            for i in range(int(num_cycles)):
                if not tactic_df.empty:
                    row = tactic_df.iloc[i].copy()
                    row["type"] = "tactic"
                    combined_rows.append(row)
                if not strategy_df.empty:
                    row = strategy_df.iloc[i].copy()
                    row["type"] = "strategy"
                    combined_rows.append(row)
                if not endgame_df.empty:
                    row = endgame_df.iloc[i].copy()
                    row["type"] = "endgame"
                    combined_rows.append(row)
            all_puzzles = pd.DataFrame(combined_rows)

        puzzles = []
        for _, row in all_puzzles.iterrows():
            # Map CSV columns to Puzzle model
            # Assuming CSV has: id, fen, moves, rating, rating_deviation,
            # popularity, nb_plays, themes, game_url, opening_tags
            # Note: column names might be capitalized in CSV (PuzzleId, FEN, Moves...)
            # We'll try to find both.

            p = Puzzle(
                id=str(self._get_val(row, ["id", "PuzzleId"])),
                fen=str(self._get_val(row, ["fen", "FEN"])),
                moves=str(self._get_val(row, ["moves", "Moves"])),
                rating=int(self._get_val(row, ["rating", "Rating"], 1500)),
                rating_deviation=int(
                    self._get_val(row, ["rating_deviation", "RatingDeviation"], 350)
                ),
                popularity=int(self._get_val(row, ["popularity", "Popularity"], 100)),
                nb_plays=int(self._get_val(row, ["nb_plays", "NbPlays"], 100)),
                themes=str(self._get_val(row, ["themes", "Themes"], "")),
                game_url=str(self._get_val(row, ["game_url", "GameUrl"], "")),
                opening_tags=str(self._get_val(row, ["opening_tags", "OpeningTags"], "")),
                type=str(row.get("type", "unknown")),
            )
            puzzles.append(p)

        self.repo.save_puzzles(puzzles)
        logger.info(f"Successfully seeded {len(puzzles)} puzzles to database.")
