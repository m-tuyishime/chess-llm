import logging
import traceback
import asyncio
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
        self.logger.debug(f"Updating rating with {len(puzzle_wins)} new results.")
        self.llm.player.update_player(puzzle_ratings, puzzle_deviations, puzzle_wins)
        new_rating = self.llm.player.rating
        new_rd = self.llm.player.rd
        new_vol = self.llm.player.vol

        self.logger.info(f"Updated rating: {new_rating:.2f} (RD: {new_rd:.2f}) Vol: {new_vol:.6f}")
        return new_rating, new_rd, new_vol

    async def evaluate_puzzle(self, puzzle:pd.Series) -> Optional[Tuple[int, Tuple[int, int, bool]]]:
        """
        Evaluate a single puzzle. On error, exit early; do not complete the puzzle.
        Returns (puzzle_rating, puzzle_deviation, success_flag) if evaluated successfully, else None.
        Does NOT update the LLM rating itself.
        """
        puzzle_id = puzzle.id
        puzzle_type = puzzle.type
        self.logger.info(f"Starting evaluation of puzzle {puzzle_id} (type: {puzzle_type})")

        db = self.db_manager
        fen = puzzle.fen
        solution = puzzle.moves.split(" ")
        puzzle_rating = int(puzzle.rating) # Ensure type
        puzzle_deviation = int(puzzle.rating_deviation) # Ensure type

        self.logger.debug(f"Puzzle {puzzle_id}: Initial FEN: {fen}")
        self.logger.debug(f"Puzzle {puzzle_id}: Solution moves: {solution}")

        game_id = db.create_game(puzzle_id, self.llm.model_name) # Create a new game entry in the database
        self.logger.info(f"Created game_id {game_id} for puzzle {puzzle_id}")

        chess_env = ChessEnv(fen) # Initialize the chess environment with the puzzle's FEN
        failed_puzzle = False

        # Iterate through the moves of the solution in pairs (opponent's move, model's move)
        for i in range(0, len(solution), 2):
            # Play the opponent's move
            opponent_move = chess_env.uci_to_san(solution[i])
            self.logger.debug(f"Puzzle {puzzle_id}: Opponent move {i//2+1}: {opponent_move}")
            fen = chess_env.apply_move(opponent_move)
            db.save_move(game_id, fen, opponent_move, opponent_move, 0, 0, False)

            # Generate the model's move
            color = chess_env.get_turn_color() 
            legal_moves_san = chess_env.get_legal_moves()
            expected_move = chess_env.uci_to_san(solution[i+1])
            self.logger.debug(f"Puzzle {puzzle_id}: Expected model move: {expected_move}")

            move, prompt_tokens, completion_tokens = await self.llm.get_move(fen, legal_moves_san, color)

            if move is None:
                self.logger.error(f"Puzzle {puzzle_id}: Model failed to generate move, exiting early")
                return None # Indicate critical error

            self.logger.info(f"Puzzle {puzzle_id}: Model move: {move} (expected: {expected_move})")

            illegal_moves_san = []
            while not chess_env.is_move_legal(move) and len(illegal_moves_san) < 5:
                self.logger.warning(f"Puzzle {puzzle_id}: Illegal move {move}, retrying")
                illegal_moves_san.append(move)
                # Save the illegal move attempt
                db.save_move(game_id, fen, expected_move, move, prompt_tokens, completion_tokens, True)
                move, prompt_tokens, completion_tokens = await self.llm.retry_move(illegal_moves_san, fen, legal_moves_san, color)
                if move is None:
                    self.logger.error(f"Puzzle {puzzle_id}: Evaluation failed during retry, exiting early")
                    return None # Indicate critical error
                self.logger.debug(f"Puzzle {puzzle_id}: Retry generated move: {move}")


            if not chess_env.is_move_legal(move):
                self.logger.warning(f"Puzzle {puzzle_id}: Move {move} still illegal after retries")
                # Save the final illegal move attempt
                db.save_move(game_id, fen, expected_move, move, prompt_tokens, completion_tokens, True)
                failed_puzzle = True
                break

            new_fen = chess_env.apply_move(move)
            db.save_move(game_id, new_fen, expected_move, move, prompt_tokens, completion_tokens, False)
            fen = new_fen 

            # Check if the move matches the expected move
            if move != expected_move:
                self.logger.info(f"Puzzle {puzzle_id}: Move {move} doesn't match expected {expected_move}")
                failed_puzzle = True
                break

        result_str = "SUCCESS" if not failed_puzzle else "FAILURE"
        self.logger.info(f"Puzzle {puzzle_id} evaluation complete: {result_str}")
        db.update_game_result(game_id, failed_puzzle)
        # Do not update rating or save benchmarks here, return results for batch update
        return game_id, (puzzle_rating, puzzle_deviation, not failed_puzzle)

    async def evaluate_all(self, target_deviation: Optional[int] = None, max_concurrent: int = 6) -> None:
        if self.puzzles_df.empty:
            self.logger.info("No puzzles to evaluate.")
            return

        self.logger.info(f"Evaluating {len(self.puzzles_df)} puzzles (concurrency={max_concurrent}, target_deviation={target_deviation})")
        sem = asyncio.Semaphore(max_concurrent)

        async def sem_task(puzzle, name):
            async with sem:
                result = await self.evaluate_puzzle(puzzle)
                if result is None:
                    self.logger.warning(f"{name} returned no result, skipping benchmark.")
                    return name, None

                # immediately update rating & write a benchmark
                game_id, (puzz_rating, puzz_deviation, success) = result
                model_rating, model_rd, model_vol = self.update_llm_rating([puzz_rating], [puzz_deviation], [success])
                self.db_manager.save_benchmarks(game_id, model_rating, model_rd, model_vol)
                self.logger.info(
                    f"{name} → r={puzz_rating} rd={puzz_deviation} win={success} | "
                    f"new LLM: {model_rating:.1f}±{model_rd:.1f}"
                )
                return name, (puzz_rating, puzz_deviation, success, model_rd)

        tasks = [
            asyncio.create_task(sem_task(p, f"Puzzle-{p.id}"), name=f"Puzzle-{p.id}")
            for p in self.puzzles_df.itertuples()
        ]

        try:
            for coro in asyncio.as_completed(tasks):
                name, payload = await coro
                if payload is None:
                    continue
                _, _, _, model_rd = payload
                if target_deviation is not None and model_rd <= target_deviation:
                    self.logger.info(f"Target RD={target_deviation} reached, cancelling rest.")
                    for t in tasks:
                        if not t.done():
                            t.cancel()
                    break
        finally:
            await asyncio.gather(*tasks, return_exceptions=True)

        final = self.llm.player
        self.logger.info(f"Final LLM Rating: {final.rating:.2f} (RD: {final.rd:.2f}) Vol: {final.vol:.6f}")