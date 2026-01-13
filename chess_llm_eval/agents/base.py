from abc import ABC, abstractmethod

import glicko2

from chess_llm_eval.core.types import Color, Fen, SanMove


class Agent(ABC):
    """
    Abstract base class for all chess agents.
    Handles Glicko-2 rating state and defines the playing interface.
    """

    def __init__(
        self,
        model_name: str,
        rating: float = 1500.0,
        rd: float = 350.0,
        volatility: float = 0.06,
        is_reasoning: bool = False,
        is_random: bool = False,
    ) -> None:
        self.model_name = model_name
        self.is_reasoning = is_reasoning
        self.is_random = is_random
        self.player = glicko2.Player(rating=rating, rd=rd, vol=volatility)

    @property
    def name(self) -> str:
        return self.model_name

    @property
    def rating(self) -> float:
        return float(self.player.rating)

    @property
    def rd(self) -> float:
        return float(self.player.rd)

    @property
    def volatility(self) -> float:
        return float(self.player.vol)

    def update_rating(self, ratings: list[float], rds: list[float], outcomes: list[float]) -> None:
        """
        Update the agent's rating based on a series of game outcomes.

        Args:
            ratings: List of opponent ratings.
            rds: List of opponent rating deviations.
            outcomes: List of outcomes (1.0 for win, 0.0 for loss, 0.5 for draw).
        """
        self.player.update_player(ratings, rds, outcomes)

    @abstractmethod
    async def get_move(
        self, fen: Fen, legal_moves: list[SanMove], color: Color
    ) -> tuple[SanMove, int, int] | None:
        """
        Get the best move for a given board state.

        Args:
            fen: FEN string of the current board position.
            legal_moves: List of legal moves in SAN notation.
            color: The color to play ("white" or "black").

        Returns:
            Tuple of (move_san, prompt_tokens, completion_tokens), or None if failed.
        """
        pass

    @abstractmethod
    async def retry_move(
        self, failed_moves: list[SanMove], fen: Fen, legal_moves: list[SanMove], color: Color
    ) -> tuple[SanMove, int, int] | None:
        """
        Reprompt the model for a move after failed attempts.

        Args:
            failed_moves: List of moves that were attempted and rejected (illegal).
            fen: FEN string.
            legal_moves: Legal moves SAN.
            color: Color to play.

        Returns:
             Tuple of (move_san, prompt_tokens, completion_tokens), or None if failed.
        """
        pass
