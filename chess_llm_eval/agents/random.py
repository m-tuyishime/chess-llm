import logging
import random
from typing import Any

from chess_llm_eval.agents.base import Agent
from chess_llm_eval.core.types import Color, Fen, SanMove

logger = logging.getLogger(__name__)


class RandomAgent(Agent):
    """Agent that plays random legal moves."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__("Random", is_random=True, **kwargs)

    async def get_move(
        self, fen: Fen, legal_moves: list[SanMove], color: Color
    ) -> tuple[SanMove, int, int] | None:
        if not legal_moves:
            return None
        # Simulate "thinking" very briefly? No need.
        return random.choice(legal_moves), 0, 0

    async def retry_move(
        self, failed_moves: list[SanMove], fen: Fen, legal_moves: list[SanMove], color: Color
    ) -> tuple[SanMove, int, int] | None:
        valid = [m for m in legal_moves if m not in failed_moves]
        if not valid:
            return None
        return random.choice(valid), 0, 0
