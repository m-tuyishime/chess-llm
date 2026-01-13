import contextlib
import logging
import os
from typing import Any

import chess
import chess.engine

from chess_llm_eval.agents.base import Agent
from chess_llm_eval.core.types import Color, Fen, SanMove

logger = logging.getLogger(__name__)


class StockfishAgent(Agent):
    """Agent using Stockfish engine."""

    def __init__(self, level: int = 1, **kwargs: Any) -> None:
        model_name = f"stockfish-{level}"
        super().__init__(model_name, is_reasoning=True, **kwargs)
        self.level = level

        stockfish_path = os.getenv("STOCKFISH_PATH")
        if not stockfish_path or not os.path.exists(stockfish_path):
            raise ValueError(
                "STOCKFISH_PATH env var not set or invalid. "
                "Please install Stockfish and set the path."
            )

        self.engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)
        self.engine.configure({"Skill Level": self.level})
        logger.info(f"Initialized Stockfish level {level}")

    async def get_move(
        self, fen: Fen, legal_moves: list[SanMove], color: Color
    ) -> tuple[SanMove, int, int] | None:
        board = chess.Board(fen)
        try:
            # Time limit 0.1s is fast but maybe too fast for high levels?
            # For level 1 it's fine.
            result = self.engine.play(board, chess.engine.Limit(time=0.1))
            if result.move:
                return board.san(result.move), 0, 0
            return None
        except Exception as e:
            logger.error(f"Stockfish error: {e}")
            return None

    async def retry_move(
        self,
        failed_moves: list[SanMove],
        fen: Fen,
        legal_moves: list[SanMove],
        color: Color,
    ) -> tuple[SanMove, int, int] | None:
        # Stockfish shouldn't generate illegal moves.
        # But if it does (or if we are testing robustness), try MultiPV.
        board = chess.Board(fen)
        try:
            analysis = self.engine.analyse(
                board, chess.engine.Limit(time=0.1), multipv=len(failed_moves) + 1
            )
            for info in analysis:
                if "pv" in info:
                    move = info["pv"][0]
                    san = board.san(move)
                    if san not in failed_moves:
                        return san, 0, 0
            return None
        except Exception:
            return None

    def close(self) -> None:
        self.engine.quit()

    def __del__(self) -> None:
        with contextlib.suppress(Exception):
            self.close()
