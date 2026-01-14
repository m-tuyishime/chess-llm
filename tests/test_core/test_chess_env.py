import pytest

from chess_llm_eval.core.chess_env import ChessEnv


def test_chess_env_init() -> None:
    """
    Test initialization from a FEN string.
    Why: The environment must correctly parse the starting position (FEN) to ensure
    that the puzzle setup is accurate before any moves are made.
    """
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    env = ChessEnv(fen)
    assert env.board.fen().startswith(fen.split(" ")[0])


def test_chess_env_invalid_fen() -> None:
    """
    Test error handling for invalid FEN strings.
    Why: Bad data in the puzzle set or incorrect manual input should raise a clear error
    rather than causing undefined behavior or crashes later in the game loop.
    """
    with pytest.raises(ValueError, match="Invalid FEN string"):
        ChessEnv("invalid fen")


def test_chess_env_legal_moves() -> None:
    """
    Test generation of legal moves.
    Why: Generating the correct set of legal moves is essential for validating agent outputs.
    If this is wrong, we might incorrectly mark valid moves as illegal or vice versa.
    """
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    env = ChessEnv(fen)
    moves = env.get_legal_moves()
    assert "e4" in moves
    assert "Nf3" in moves
    assert len(moves) == 20


def test_chess_env_turn_color() -> None:
    """
    Test identification of the active turn color.
    Why: The prompt generator needs to know whose turn it is to instruct the LLM correctly.
    """
    white_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    assert ChessEnv(white_fen).get_turn_color() == "white"

    black_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    assert ChessEnv(black_fen).get_turn_color() == "black"


def test_chess_env_is_move_legal() -> None:
    """
    Test strict validation of move legality.
    Why: This is the core validation logic for the benchmark. We must be able to definitively
    say whether an agent's move is allowed by the rules of chess.
    """
    env = ChessEnv("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    assert env.is_move_legal("e4") is True
    assert env.is_move_legal("e5") is False
    assert env.is_move_legal("InvalidMove") is False


def test_chess_env_apply_move() -> None:
    """
    Test applying a move to update the board state.
    Why: The environment works by state mutation. We need to verify that applying a move
    correctly transitions the board to the next state for multi-turn evaluations.
    """
    env = ChessEnv("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    env.apply_move("e4")
    assert "e4" not in env.get_legal_moves()  # It's black's turn now
    assert env.get_turn_color() == "black"


def test_chess_env_uci_to_san() -> None:
    """
    Test conversion from UCI to SAN notation.
    Why: Puzzle solutions are often in UCI (e.g., e2e4), but we prefer working with SAN (e4)
    for LLM prompts and logging. Correct conversion is vital for comparing moves.
    """
    env = ChessEnv("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    assert env.uci_to_san("e2e4") == "e4"
    with pytest.raises(ValueError, match="Invalid UCI move"):
        env.uci_to_san("invalid")
