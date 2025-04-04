import pandas as pd
import logging

from .database_manager import DatabaseManager
from .agents import LLMAgent

# ---------------------------
# Module: Sélection de puzzles
# ---------------------------
class PuzzleSelector:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.logger = logging.getLogger('chess_benchmark.puzzle_selector')

    def _get_shuffled_puzzles_from_csv(self, csv_path: str) -> pd.DataFrame:
        """
        Read a CSV file and shuffle the rows.
        """
        df = pd.read_csv(csv_path)
        shuffled_df = df.sample(frac=1).reset_index(drop=True)
        return shuffled_df

    def _get_tactic_puzzles(self) -> pd.DataFrame:
        """
        TODO: Return a DataFrame of tactic puzzles.
        """
        return self._get_shuffled_puzzles_from_csv('data/TacticDB.csv')

    def _get_strategic_puzzles(self) -> pd.DataFrame:
        """
        TODO: Return a DataFrame of strategy puzzles.
        """
        return self._get_shuffled_puzzles_from_csv('data/StrategicDB.csv')

    def _get_endgame_puzzles(self) -> pd.DataFrame:
        """
        TODO: Return a DataFrame of endgame puzzles.
        """
        return self._get_shuffled_puzzles_from_csv('data/EndgameDB.csv')

    def get_puzzles_for_model(self, llm: LLMAgent) -> pd.DataFrame:
        # First, check if any puzzles exist at all
        all_puzzles = self.db_manager.get_puzzles()
        if all_puzzles is None:
            self.logger.info("No puzzles found in the database. Generating new puzzles.")
            # Generate new puzzles selection using the existing logic
            tactic_df = self._get_tactic_puzzles()
            strategy_df = self._get_strategic_puzzles()
            endgame_df = self._get_endgame_puzzles()
            
            if any(len(df) == 0 for df in [tactic_df, strategy_df, endgame_df]):
                raise ValueError("One or more puzzle categories are empty.")
            
            num_cycles = min(len(tactic_df), len(strategy_df), len(endgame_df))
            combined_rows = []
            for i in range(num_cycles):              
                row = tactic_df.iloc[i].copy()
                row["Type"] = "tactic"
                combined_rows.append(row)
                
                row = strategy_df.iloc[i].copy()
                row["Type"] = "strategy"
                combined_rows.append(row)
                
                row = endgame_df.iloc[i].copy()
                row["Type"] = "endgame"
                combined_rows.append(row)
            
            combined_df = pd.DataFrame(combined_rows)

            self.logger.info(f"Generated {len(combined_df)} new puzzles for model {llm.model_name}")
            return self.db_manager.insert_puzzles(combined_df)
        else:
            # Return only puzzles that the model hasn't attempted
            model_puzzles = self.db_manager.get_uncompleted_puzzles_for_agent(llm.model_name)
            if model_puzzles is None or model_puzzles.empty:
                self.logger.info(f"All puzzles have already been evaluated by model {llm.model_name}. Exiting.")
                return pd.DataFrame() # Return empty DataFrame if no puzzles are available
            
            self.logger.info(f"Found {len(model_puzzles)} puzzles for model {llm.model_name}")
            return model_puzzles