import logging
import traceback
from typing import List, Optional, Tuple
import pandas as pd

from .chess_env import ChessEnv
from .database_manager import DatabaseManager
from .agents import LLMAgent

# ---------------------------
# Module: Module d'évaluation 
# ---------------------------
class Evaluator:
    def __init__(self, llm:LLMAgent, puzzles_df:pd.DataFrame):
        self.llm = llm
        self.puzzles_df = puzzles_df
        self.db_manager = DatabaseManager()
        self.logger = logging.getLogger(f'chess_benchmark.evaluator.{llm.model_name}')
        self.logger.info(f"Initialized evaluator for model {llm.model_name} with {len(puzzles_df)} puzzles")

    def update_llm_rating(self, puzzle_ratings:List[int], puzzle_deviations:List[int], puzzle_wins:List[bool]) -> Tuple[float, float, float]:
        """
        Update the LLM's rating and deviation based on the results of the puzzles.
        """
        self.logger.debug(f"Updating rating: puzzle ratings={puzzle_ratings}, wins={puzzle_wins}")
        self.llm.player.update_player(puzzle_ratings, puzzle_deviations, puzzle_wins)
        new_rating = self.llm.player.rating
        new_rd = self.llm.player.rd
        new_vol = self.llm.player.vol
        
        self.logger.info(f"Updated rating: {new_rating} (RD: {new_rd})")
        return new_rating, new_rd, new_vol
    
    async def evaluate_puzzle(self, puzzle:pd.Series) -> Optional[Tuple[float, float, float]]:
        """
        Evaluate a single puzzle. On error, exit early; do not complete the puzzle.
        Returns (rating, deviation, volatility) if evaluated.
        """
        puzzle_id = puzzle.id
        puzzle_type = getattr(puzzle, 'type', getattr(puzzle, 'Type', 'unknown'))
        self.logger.info(f"Starting evaluation of puzzle {puzzle_id} (type: {puzzle_type})")
        
        try:
            db = self.db_manager
            fen = puzzle.fen
            solution = puzzle.moves.split(" ")
            puzzle_rating = puzzle.rating
            puzzle_deviation = puzzle.rating_deviation

            self.logger.debug(f"Puzzle {puzzle_id}: Initial FEN: {fen}")
            self.logger.debug(f"Puzzle {puzzle_id}: Solution moves: {solution}")

            game_id = db.create_game(puzzle_id, self.llm.model_name)
            self.logger.info(f"Created game_id {game_id} for puzzle {puzzle_id}")
            
            chess_env = ChessEnv(fen)
            failed_puzzle = False

            # Iterate through the moves of the solution in pairs (opponent's move, model's move)
            # The number of moves in the solution should be always even
            for i in range(0, len(solution), 2):
                # Play the opponent's move
                try:
                    opponent_move = chess_env.uci_to_san(solution[i])
                    self.logger.debug(f"Puzzle {puzzle_id}: Opponent move {i//2+1}: {opponent_move}")
                    
                    # Get the new FEN after applying the opponent's move
                    fen = chess_env.apply_move(opponent_move)
                    # Save opponent move (always correct)
                    db.save_move(game_id, fen, opponent_move, opponent_move, 0, 0, False)
                except Exception as e:
                    self.logger.error(f"Failed to apply opponent move: {e}")
                    self.logger.error(traceback.format_exc())
                    failed_puzzle = True
                    break

                # Check if we're at the end of the solution
                if i+1 >= len(solution):
                    self.logger.warning(f"Puzzle {puzzle_id}: Odd number of moves in solution, ending after opponent's move")
                    break

                # Get the color of the side to move
                color = chess_env.get_turn_color()
                # Get the legal moves for the current position
                legal_moves_san = chess_env.get_legal_moves()
                # Get the expected move from the solution
                expected_move = chess_env.uci_to_san(solution[i+1])
                self.logger.debug(f"Puzzle {puzzle_id}: Expected model move: {expected_move}")
                
                # LLM generates a move
                move, prompt_tokens, completion_tokens = await self.llm.get_move(fen, legal_moves_san, color)

                if move is None:
                    self.logger.error(f"Puzzle {puzzle_id}: Model failed to generate move, exiting early")
                    # Exit this task early request error, leaving puzzle uncompleted
                    return None
                
                self.logger.info(f"Puzzle {puzzle_id}: Model move: {move} (expected: {expected_move})")
                
                # Store the illegal moves
                illegal_moves_san = []
                # Retry until a legal move is found or 5 illegal moves are stored
                while not chess_env.is_move_legal(move) and len(illegal_moves_san) < 5:
                    self.logger.warning(f"Puzzle {puzzle_id}: Illegal move {move}, retrying")
                    illegal_moves_san.append(move)
                    move, prompt_tokens, completion_tokens = await self.llm.retry_move(illegal_moves_san, fen, legal_moves_san, color)
                    if move is None:
                        self.logger.error(f"Puzzle {puzzle_id}: Evaluation failed during retry, exiting early")
                        # Exit this task early request error, leaving puzzle uncompleted
                        return None
                    
                    # store the illegal move
                    db.save_move(game_id, fen, expected_move, move, prompt_tokens, completion_tokens, True)
                    self.logger.debug(f"Puzzle {puzzle_id}: Retry generated move: {move}")

                # If the move is still illegal after retries, mark the puzzle as failed (terminal move)
                if not chess_env.is_move_legal(move):
                    self.logger.warning(f"Puzzle {puzzle_id}: Move {move} still illegal after retries")
                    failed_puzzle = True
                    db.save_move(game_id, fen, expected_move, move, prompt_tokens, completion_tokens, False)
                    break

                # Apply the move to the board and get the new FEN
                try:
                    fen = chess_env.apply_move(move)
                    db.save_move(game_id, fen, expected_move, move, prompt_tokens, completion_tokens, False)
                except Exception as e:
                    self.logger.error(f"Failed to apply model move: {e}")
                    self.logger.error(traceback.format_exc())
                    failed_puzzle = True
                    break

                # If the move doesn't match the expected move, mark the puzzle as failed (terminal move)
                if move != expected_move:
                    self.logger.info(f"Puzzle {puzzle_id}: Move {move} doesn't match expected {expected_move}")
                    failed_puzzle = True
                    break

            # Update benchmarks based on outcome
            result = "SUCCESS" if not failed_puzzle else "FAILURE"
            self.logger.info(f"Puzzle {puzzle_id} evaluation complete: {result}")
            # Set the game's failed field based on puzzle outcome (False for success, True for failure)
            db.update_game_result(game_id, failed_puzzle)
            rating, deviation, volatility = self.update_llm_rating([puzzle_rating], [puzzle_deviation], [not failed_puzzle])
            db.save_benchmarks(game_id, rating, deviation, volatility)
            return (rating, deviation, volatility)
            
        except Exception as e:
            self.logger.error(f"Error evaluating puzzle {puzzle_id}: {e}")
            self.logger.error(traceback.format_exc())
            return None

    async def evaluate_all(self, target_deviation: int) -> None:
        """
        Evaluate all puzzles sequentially until target deviation is reached.
        """
        if self.puzzles_df.empty:
            self.logger.info("No puzzles to evaluate.")
            return

        self.logger.info(f"Starting sequential evaluation of {len(self.puzzles_df)} puzzles (target deviation: {target_deviation})")
        completed = 0

        for puzzle in self.puzzles_df.itertuples():
            result = await self.evaluate_puzzle(puzzle)
            if result is None:
                self.logger.warning(f"Puzzle {puzzle.id} returned None")
                continue

            completed += 1
            _, deviation, _ = result
            self.logger.info(f"Completed {completed}/{len(self.puzzles_df)} puzzles. Current deviation: {deviation}")

            if deviation < target_deviation:
                self.logger.info(f"Target deviation {target_deviation} reached, stopping evaluation")
                break

        self.logger.info(f"Evaluation complete: {completed}/{len(self.puzzles_df)} puzzles evaluated")