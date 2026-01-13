import asyncio
import logging
from dataclasses import dataclass

from chess_llm_eval.agents.base import Agent
from chess_llm_eval.core.chess_env import ChessEnv
from chess_llm_eval.core.types import SanMove
from chess_llm_eval.data.models import MoveRecord, Puzzle
from chess_llm_eval.data.protocols import GameRepository

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    game_id: int
    puzzle_rating: int
    puzzle_deviation: int
    success: bool
    agent_rd: float


class Evaluator:
    """Orchestrates the evaluation of chess puzzles by agents."""

    def __init__(self, agent: Agent, puzzles: list[Puzzle], repository: GameRepository) -> None:
        self.agent = agent
        self.puzzles = puzzles
        self.repository = repository
        self.logger = logging.getLogger(f"chess_llm_eval.evaluator.{agent.name}")
        self.logger.info(
            f"Initialized evaluator for agent {agent.name} with {len(puzzles)} puzzles"
        )

    def update_agent_rating(
        self, puzzle_ratings: list[int], puzzle_deviations: list[int], puzzle_wins: list[bool]
    ) -> tuple[float, float, float]:
        """Update the agent's rating based on the results of the puzzles."""
        self.logger.debug(f"Updating rating with {len(puzzle_wins)} new results.")

        # Convert types for glicko2
        outcomes = [1.0 if w else 0.0 for w in puzzle_wins]
        r_opp = [float(r) for r in puzzle_ratings]
        rd_opp = [float(d) for d in puzzle_deviations]

        self.agent.update_rating(r_opp, rd_opp, outcomes)

        new_rating = self.agent.rating
        new_rd = self.agent.rd
        new_vol = self.agent.volatility

        self.logger.info(f"Updated rating: {new_rating:.2f} (RD: {new_rd:.2f}) Vol: {new_vol:.6f}")
        return new_rating, new_rd, new_vol

    async def evaluate_puzzle(self, puzzle: Puzzle) -> tuple[int, tuple[int, int, bool]] | None:
        """
        Evaluate a single puzzle.
        Returns (game_id, (puzzle_rating, puzzle_deviation, success_flag)) or None if error.
        """
        self.logger.info(f"Starting evaluation of puzzle {puzzle.id} (type: {puzzle.type})")

        try:
            game_id = self.repository.create_game(puzzle.id, self.agent.name)
            self.logger.info(f"Created game_id {game_id} for puzzle {puzzle.id}")
        except Exception as e:
            self.logger.error(f"Failed to create game for puzzle {puzzle.id}: {e}")
            return None

        chess_env = ChessEnv(puzzle.fen)
        failed_puzzle = False
        solution = puzzle.moves.split(" ")

        # Iterate through solution moves in pairs (opponent, model)
        for i in range(0, len(solution), 2):
            # 1. Opponent's move
            try:
                opponent_move_uci = solution[i]
                opponent_move_san = chess_env.uci_to_san(opponent_move_uci)
                fen_before = chess_env.board.fen()
                chess_env.apply_move(opponent_move_san)
                # fen_after = chess_env.board.fen() # Unused

                # Save opponent move
                self.repository.save_move(
                    game_id,
                    MoveRecord(
                        fen=fen_before,
                        expected_move=opponent_move_san,
                        actual_move=opponent_move_san,
                        is_illegal=False,
                        game_id=game_id,
                    ),
                )
            except Exception as e:
                self.logger.error(f"Error processing opponent move {solution[i]}: {e}")
                return None

            # 2. Model's move
            try:
                expected_move_uci = solution[i + 1]
                expected_move_san = chess_env.uci_to_san(expected_move_uci)
            except IndexError:
                # Puzzle might end on opponent move (unlikely for tactic puzzles but possible)
                break

            color = chess_env.get_turn_color()
            legal_moves = chess_env.get_legal_moves()
            fen_for_model = chess_env.board.fen()

            self.logger.debug(f"Expected model move: {expected_move_san}")

            # Get move from agent
            result = await self.agent.get_move(fen_for_model, legal_moves, color)

            if not result:
                self.logger.error("Agent failed to generate move")
                failed_puzzle = True
                break

            move_san, pt, ct = result
            self.logger.info(f"Model move: {move_san}")

            # Handle illegal moves
            illegal_attempts: list[SanMove] = []
            final_move_san = move_san

            if not chess_env.is_move_legal(move_san):
                failed_puzzle = (
                    True  # Initially assume failure unless corrected (but actually retry logic)
                )
                # Wait, original logic retried 5 times. If strictly illegal, we retry.

                while len(illegal_attempts) < 5:
                    self.logger.warning(f"Illegal move {final_move_san}, retrying")
                    illegal_attempts.append(final_move_san)

                    self.repository.save_move(
                        game_id,
                        MoveRecord(
                            fen=fen_for_model,
                            expected_move=expected_move_san,
                            actual_move=final_move_san,
                            is_illegal=True,
                            prompt_tokens=pt,
                            completion_tokens=ct,
                            game_id=game_id,
                        ),
                    )

                    retry_result = await self.agent.retry_move(
                        illegal_attempts, fen_for_model, legal_moves, color
                    )
                    if not retry_result:
                        break  # Failed to retry

                    final_move_san, pt, ct = retry_result
                    if chess_env.is_move_legal(final_move_san):
                        failed_puzzle = False  # Recovered
                        break

            # Check legality one last time
            if not chess_env.is_move_legal(final_move_san):
                self.logger.error(f"Move {final_move_san} still illegal after retries")
                self.repository.save_move(
                    game_id,
                    MoveRecord(
                        fen=fen_for_model,
                        expected_move=expected_move_san,
                        actual_move=final_move_san,
                        is_illegal=True,
                        prompt_tokens=pt,
                        completion_tokens=ct,
                        game_id=game_id,
                    ),
                )
                failed_puzzle = True
                break

            # Apply valid move
            chess_env.apply_move(final_move_san)
            self.repository.save_move(
                game_id,
                MoveRecord(
                    fen=fen_for_model,
                    expected_move=expected_move_san,
                    actual_move=final_move_san,
                    is_illegal=False,
                    prompt_tokens=pt,
                    completion_tokens=ct,
                    game_id=game_id,
                ),
            )

            # Check correctness against solution
            if final_move_san != expected_move_san:
                self.logger.info(f"Move {final_move_san} != Expected {expected_move_san}")
                failed_puzzle = True
                break

        self.repository.update_game_result(game_id, failed_puzzle)
        return game_id, (puzzle.rating, puzzle.rating_deviation, not failed_puzzle)

    async def evaluate_all(
        self, target_deviation: float | None = None, max_concurrent: int = 6
    ) -> None:
        """Run evaluation on all puzzles concurrently."""
        if not self.puzzles:
            self.logger.info("No puzzles to evaluate.")
            return

        self.logger.info(f"Evaluating {len(self.puzzles)} puzzles (concurrency={max_concurrent})")
        sem = asyncio.Semaphore(max_concurrent)

        async def sem_task(puzzle: Puzzle) -> tuple[int, int, bool, float] | None:
            async with sem:
                result = await self.evaluate_puzzle(puzzle)
                if result is None:
                    return None

                game_id, (pr, pd, success) = result
                nr, nrd, nvol = self.update_agent_rating([pr], [pd], [success])

                self.repository.save_benchmark(game_id, nr, nrd, nvol)
                return (pr, pd, success, nrd)

        tasks = [asyncio.create_task(sem_task(p)) for p in self.puzzles]

        # Wait for all tasks
        completed_count = 0
        for coro in asyncio.as_completed(tasks):
            res = await coro
            if res:
                completed_count += 1
                _, _, _, current_rd = res
                if target_deviation and current_rd <= target_deviation:
                    self.logger.info(
                        f"Target RD {target_deviation} reached. Cancelling remaining tasks."
                    )
                    for t in tasks:
                        if not t.done():
                            t.cancel()
                    break

        self.logger.info(f"Evaluation complete. Processed {completed_count} puzzles.")
