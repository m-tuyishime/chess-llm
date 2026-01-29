import pytest

from chess_llm_eval.data.sqlite import SQLiteRepository


@pytest.fixture
def memory_db() -> SQLiteRepository:
    """Creates an in-memory SQLite database with the schema."""
    repo = SQLiteRepository(":memory:")
    return repo


def test_group_concat_order(memory_db: SQLiteRepository) -> None:
    """
    Verifies that the group_concat logic in get_solutionary_agent_moves
    (and similar methods) preserves the correct order of moves.

    Why:
        SQLite's group_concat does not guarantee order by default.
        We rely on specific subquery ordering (SELECT * FROM move ORDER BY id)
        to ensure chess moves are reconstructed in the correct sequence.
        This test prevents regression of this critical logic.
    """
    # 1. Setup Data
    # Create a puzzle
    memory_db.conn.execute("INSERT INTO puzzle (id, moves) VALUES ('p1', 'e2e4 e7e5')")

    # Create a game
    cursor = memory_db.conn.execute(
        "INSERT INTO game (puzzle_id, agent_name, failed) VALUES ('p1', 'agent1', 0)"
    )
    game_id = cursor.lastrowid

    # Insert moves in a specific order
    moves = ["e2e4", "e7e5", "g1f3", "b8c6"]
    for i, m in enumerate(moves):
        memory_db.conn.execute(
            """
            INSERT INTO move (game_id, fen, correct_move, move, illegal_move)
            VALUES (?, ?, ?, ?, 0)
            """,
            (game_id, f"fen_{i}", "x", m),
        )
    memory_db.conn.commit()

    # 2. Query
    # This uses the method we want to test
    df = memory_db.get_solutionary_agent_moves()

    # 3. Verify
    assert not df.empty, "DataFrame should not be empty"
    actual_moves = df.iloc[0]["agent_moves"]
    # Wait, the code uses group_concat(m.move, ' ') - space separator.

    expected_moves_space = "e2e4 e7e5 g1f3 b8c6"

    assert actual_moves == expected_moves_space, (
        f"Moves order mismatch. Expected '{expected_moves_space}', got '{actual_moves}'"
    )
