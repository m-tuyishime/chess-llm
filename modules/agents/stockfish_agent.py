import os
import logging
import asyncio
import chess
import chess.engine
from typing import List, Optional, Tuple

from .agent import Agent

class StockfishAgent(Agent):
    """
    A chess engine agent using Stockfish at a specified skill level.
    """

    def __init__(self, level: int = 1):
        self.model_name = f"stockfish-{level}_agent"
        super().__init__(self.model_name, is_random=False, is_reasoning=True)
        self.level = level
        self.logger = logging.getLogger(f'chess_benchmark.stockfish_agent.{self.model_name}')
        self.logger.info(f"Initializing StockfishAgent with model name: {self.model_name} and level: {self.level}")
        # Launch Stockfish engine 
        STOCKFISH_PATH = os.getenv("STOCKFISH_PATH")
        self.logger.debug(f"Launching Stockfish engine from path: {STOCKFISH_PATH}")

        if not STOCKFISH_PATH or not os.path.exists(STOCKFISH_PATH):
            raise ValueError("STOCKFISH_PATH environment variable is not set or the path does not exist.")
    
        self.engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
        self.engine.configure({"Skill Level": self.level})

    async def get_move(self, fen: str, legal_moves_san: List[str], color: str) -> Optional[Tuple[str, int, int]]:
        """
        Returns a tuple (move, 0, 0) to simulate prompt and completion tokens.
        """
        self.logger.debug(f"StockfishAgent analyzing board for FEN: {fen}")
        board = chess.Board(fen)

        # Analyze with a short time limit 
        result = self.engine.play(board, chess.engine.Limit(time=0.01))
        move = result.move

        if move is None:
            self.logger.error("StockfishAgent failed to find a move.")
            return None

        move_san = board.san(move)
        self.logger.info(f"StockfishAgent selected move: {move_san}")
        return move_san, 0, 0

    
    async def retry_move(self, failed_moves_san: List[str], fen: str, legal_moves_san: List[str], color: str) -> Optional[Tuple[str, int, int]]:
        """
        Retry move that are not in the failed moves list.
        """
        self.logger.debug(f"StockfishAgent retry_move called. Failed moves: {failed_moves_san}, FEN: {fen}")
        board = chess.Board(fen)

        # Request multiple principal variations
        analysis = self.engine.analyse(board, chess.engine.Limit(time=0.1), multipv=3)
        # analysis is a list when multipv > 1
        for info in analysis:
            move = info["pv"][0]
            move_san = board.san(move) 
            if move_san not in failed_moves_san:
                self.logger.info(f"StockfishAgent retry_move selected move: {move_san}")
                return move_san, 0, 0
            
    def close(self):
        """Closes the Stockfish engine."""
        # Check if engine exists and is running before quitting
        if self.engine is not None:
             try:
                 self.logger.info("Closing Stockfish engine.")
                 self.engine.quit()
             except chess.engine.EngineTerminatedError:
                 self.logger.warning("Stockfish engine already terminated.")
             except Exception as e:
                 self.logger.error(f"Error closing Stockfish engine: {e}")
        else:
             self.logger.info("Stockfish engine was not running or already closed.")
    
    def __del__(self):
        """Destructor to ensure the engine is closed."""
        self.close()
