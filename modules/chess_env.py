import chess
import logging
from typing import List

# ---------------------------
# Module: Environnement de jeu 
# ---------------------------
class ChessEnv:
    def __init__(self, fen):
        self.board = chess.Board(fen)
        self.logger = logging.getLogger('chess_benchmark.environment')
        self.logger.debug(f"Created board with FEN: {fen}")

    def get_legal_moves(self) -> List:
        """
        Returns the list of legal moves in SAN notation.
        """
        legal_moves = [self.board.san(move) for move in self.board.legal_moves]
        self.logger.debug(f"Legal moves: {legal_moves}")
        return legal_moves
    
    def get_turn_color(self) -> str:
        """
        Returns the color of the side to move ('white' or 'black').
        """
        color = "white" if self.board.turn == chess.WHITE else "black"
        self.logger.debug(f"Turn color: {color}")
        return color

    def is_move_legal(self, move_san: str) -> bool:
        """
        Checks if a given move (in SAN) is legal in the current board state.
        """
        is_legal = move_san in self.get_legal_moves()
        if not is_legal:
            self.logger.debug(f"Move {move_san} is not legal")
        return is_legal

    def apply_move(self, move_san: str) -> str:
        """
        Applies the move to the board and returns the new FEN string.
        """
        try:
            self.board.push_san(move_san)
            new_fen = self.board.fen()
            self.logger.debug(f"Applied move {move_san}, new FEN: {new_fen}...")
            return new_fen
        except Exception as e:
            self.logger.error(f"Error applying move {move_san}: {e}")
            raise
            
    def uci_to_san(self, uci: str) -> str:
        """
        Convert UCI move to SAN move.
        """
        try:
            san = self.board.san(chess.Move.from_uci(uci))
            self.logger.debug(f"Converted UCI {uci} to SAN {san}")
            return san
        except Exception as e:
            self.logger.error(f"Error converting UCI {uci} to SAN: {e}")
            raise