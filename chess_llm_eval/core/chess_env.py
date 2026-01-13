import logging

import chess

from chess_llm_eval.core.types import Color, Fen, SanMove, UciMove

logger = logging.getLogger(__name__)


class ChessEnv:
    """Wrapper around python-chess board state."""

    def __init__(self, fen: Fen) -> None:
        try:
            self.board = chess.Board(fen)
            logger.debug(f"Created board with FEN: {fen}")
        except ValueError as e:
            logger.error(f"Invalid FEN string: {fen}")
            raise ValueError(f"Invalid FEN string: {fen}") from e

    def get_legal_moves(self) -> list[SanMove]:
        """Returns the list of legal moves in SAN notation."""
        legal_moves = [self.board.san(move) for move in self.board.legal_moves]
        logger.debug(f"Legal moves: {legal_moves}")
        return legal_moves

    def get_turn_color(self) -> Color:
        """Returns the color of the side to move."""
        color: Color = "white" if self.board.turn == chess.WHITE else "black"
        logger.debug(f"Turn color: {color}")
        return color

    def is_move_legal(self, move_san: SanMove) -> bool:
        """Checks if a given move (in SAN) is legal in the current board state."""
        try:
            # python-chess 'parse_san' validates semantics (ambiguity, legality)
            # strictly speaking 'san' generation is one way, 'parse_san' is the check
            # But checking against get_legal_moves string list is robust for LLM output matching
            is_legal = move_san in self.get_legal_moves()
            if not is_legal:
                logger.debug(f"Move {move_san} is not legal")
            return is_legal
        except ValueError:
            return False

    def apply_move(self, move_san: SanMove) -> Fen:
        """
        Applies the move to the board and returns the new FEN string.
        Raises ValueError if move is illegal or invalid.
        """
        try:
            self.board.push_san(move_san)
            new_fen = self.board.fen()
            logger.debug(f"Applied move {move_san}, new FEN: {new_fen}")
            return new_fen
        except ValueError as e:
            logger.error(f"Error applying move {move_san}: {e}")
            raise ValueError(f"Illegal or invalid move: {move_san}") from e

    def uci_to_san(self, uci: UciMove) -> SanMove:
        """Convert UCI move to SAN move."""
        try:
            san = self.board.san(chess.Move.from_uci(uci))
            logger.debug(f"Converted UCI {uci} to SAN {san}")
            return san
        except ValueError as e:
            # Fallback or re-raise? Re-raising is safer for correctness
            logger.error(f"Error converting UCI {uci} to SAN: {e}")
            raise ValueError(f"Invalid UCI move: {uci}") from e
