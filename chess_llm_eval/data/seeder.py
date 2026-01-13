import pandas as pd
import logging
import os
from chess_llm_eval.data.sqlite import SQLiteRepository
from chess_llm_eval.data.models import Puzzle

logger = logging.getLogger(__name__)

class PuzzleSeeder:
    """Helper class to seed the database with puzzles from CSV files."""
    
    def __init__(self, repository: SQLiteRepository):
        self.repo = repository

    def _get_shuffled_puzzles_from_csv(self, csv_path: str) -> pd.DataFrame:
        if not os.path.exists(csv_path):
            logger.warning(f"CSV file not found: {csv_path}")
            return pd.DataFrame()
        df = pd.read_csv(csv_path)
        return df.sample(frac=1).reset_index(drop=True)

    def seed_from_standard_paths(self):
        """
        Seeds the database using the standard tactic, strategy, and endgame CSVs
        if they exist in the 'data' directory.
        """
        tactic_df = self._get_shuffled_puzzles_from_csv('data/TacticDB.csv')
        strategy_df = self._get_shuffled_puzzles_from_csv('data/StrategicDB.csv')
        endgame_df = self._get_shuffled_puzzles_from_csv('data/EndgameDB.csv')
        
        if tactic_df.empty and strategy_df.empty and endgame_df.empty:
            logger.info("No puzzle CSVs found to seed.")
            return

        # Interleave puzzles to ensure balanced categories if limited
        num_cycles = min(
            len(tactic_df) if not tactic_df.empty else float('inf'),
            len(strategy_df) if not strategy_df.empty else float('inf'),
            len(endgame_df) if not endgame_df.empty else float('inf')
        )
        
        if num_cycles == float('inf'):
            # Just take what we have
            all_puzzles = pd.concat([tactic_df, strategy_df, endgame_df])
        else:
            combined_rows = []
            for i in range(num_cycles):
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
            # Assuming CSV has: id, fen, moves, rating, rating_deviation, popularity, nb_plays, themes, game_url, opening_tags
            # Note: column names might be capitalized in CSV (PuzzleId, FEN, Moves...)
            # We'll try to find both.
            
            def get_val(names, default=None):
                for name in names:
                    if name in row: return row[name]
                return default

            p = Puzzle(
                id=str(get_val(["id", "PuzzleId"])),
                fen=get_val(["fen", "FEN"]),
                moves=get_val(["moves", "Moves"]),
                rating=int(get_val(["rating", "Rating"], 1500)),
                rating_deviation=int(get_val(["rating_deviation", "RatingDeviation"], 350)),
                popularity=int(get_val(["popularity", "Popularity"], 100)),
                nb_plays=int(get_val(["nb_plays", "NbPlays"], 100)),
                themes=get_val(["themes", "Themes"], ""),
                game_url=get_val(["game_url", "GameUrl"], ""),
                opening_tags=get_val(["opening_tags", "OpeningTags"], ""),
                type=row.get("type", "unknown")
            )
            puzzles.append(p)
            
        self.repo.save_puzzles(puzzles)
        logger.info(f"Successfully seeded {len(puzzles)} puzzles to database.")
