import random
import logging
from typing import List, Optional, Tuple

from .agent import Agent

class RandomAgent(Agent):
    """
    RandomAgent chooses a move randomly from the list of legal moves.
    """
    model_name = "random_agent"

    def __init__(self):
        super().__init__(self.model_name, is_random=True, is_reasoning=False)
        self.logger = logging.getLogger(f'chess_benchmark.random_agent.{self.model_name}')
        self.logger.info(f"Initializing RandomAgent with model name: {self.model_name}")

    async def get_move(self, fen: str, legal_moves_san: List[str], color: str) -> Optional[Tuple[str, int, int]]:
        """
        Get a random move from the list of legal moves.
        Returns a tuple (move, 0, 0) to simulate prompt and completion tokens.
        """
        self.logger.debug(f"RandomAgent choosing move from legal moves: {legal_moves_san}")
        if not legal_moves_san:
            self.logger.error("No legal moves provided.")
            return None, None, None

        move = random.choice(legal_moves_san)
        self.logger.info(f"RandomAgent selected move: {move}")
        return move, 0, 0

    async def retry_move(self, failed_moves_san: List[str], fen: str, legal_moves_san: List[str], color: str) -> Optional[Tuple[str, int, int]]:
        """
        Retry move is implemented by choosing another random move from available moves 
        that are not in the failed moves list.
        """
        self.logger.debug("RandomAgent retry_move called.")
        available_moves = [move for move in legal_moves_san if move not in failed_moves_san]
        if not available_moves:
            self.logger.warning("No legal moves available after excluding failed moves; using all legal moves.")
            available_moves = legal_moves_san

        move = random.choice(available_moves)
        self.logger.info(f"RandomAgent retry_move selected move: {move}")
        return move, 0, 0