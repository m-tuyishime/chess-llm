import logging
import glicko2
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from ..database_manager import DatabaseManager


# ---------------------------
# Module: Agent
# ---------------------------
class Agent(ABC):
    def __init__(self, model_name:str, is_random=False, is_reasoning=False):
        self.model_name = model_name
        self.is_reasoning = is_reasoning
        self.is_random = is_random

        logger = logging.getLogger(f'chess_benchmark.agent.{model_name}')

        # Create the llm in the database
        DatabaseManager().create_agent(model_name, is_reasoning, is_random)

        # Get the model's rating and deviation from the database
        last_benchmark = DatabaseManager().get_last_benchmarks(model_name)
        if last_benchmark:
            self.player = glicko2.Player(
                rating=last_benchmark[0],
                rd=last_benchmark[1],
                vol=last_benchmark[2]
            )
            logger.info(f"Loaded existing rating: {last_benchmark[0]} (RD: {last_benchmark[1]})")
        else:
            # If no benchmark exists, create a new player with default values
            self.player = glicko2.Player()
            logger.info(f"Creating new player with default rating: {self.player.rating}")
    
    @abstractmethod
    async def get_move(self, fen:str, legal_moves_san:List[str], color:str) -> Optional[Tuple[str, int, int]]:
        """
        Get the best move for a given board state.
        """
        pass
    
    @abstractmethod
    async def retry_move(self, failed_moves_san:List[str], fen:str, legal_moves_san:List[str], color:str) -> Optional[Tuple[str, int, int]]:
        """
        Reprompt the model for a move after a failed attempt.
        """
        pass