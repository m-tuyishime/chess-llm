import pytest

from chess_llm_eval.data.models import AgentData, MoveRecord, Puzzle
from chess_llm_eval.data.sqlite import SQLiteRepository


@pytest.fixture
def repo() -> SQLiteRepository:
    # Use in-memory database for testing
    return SQLiteRepository(":memory:")


def test_sqlite_create_tables(repo: SQLiteRepository) -> None:
    """
    Test that all required tables are created.
    Why: The application relies on a specific schema (puzzle, agent, game, move, benchmark).
    If tables are missing, the application will crash on startup or first write.
    """
    # Check if tables exist
    cursor = repo.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    assert "puzzle" in tables
    assert "agent" in tables
    assert "game" in tables
    assert "move" in tables
    assert "benchmark" in tables


def test_sqlite_agent_ops(repo: SQLiteRepository) -> None:
    """
    Test saving and retrieving agent data.
    Why: Agents are the primary entities in the system. We need to ensure we can
    persist their configuration and current rating state correctly.
    """
    agent = AgentData(name="test_agent", is_reasoning=False, is_random=False, rating=1200.0)
    repo.save_agent(agent)

    loaded = repo.get_agent("test_agent")
    assert loaded is not None
    assert loaded.name == "test_agent"
    assert loaded.rating == 1200.0

    agents = repo.get_all_agents()
    assert len(agents) == 1
    assert agents[0].name == "test_agent"


def test_sqlite_puzzle_ops(repo: SQLiteRepository) -> None:
    """
    Test saving and retrieving puzzles.
    Why: Puzzles drive the evaluation. We need to verify we can bulk save them (seeding)
    and retrieve them (evaluating), including filtering for uncompleted ones.
    """
    puzzles = [
        Puzzle(
            id="p1",
            fen="fen1",
            moves="m1 m2",
            rating=1000,
            rating_deviation=100,
            themes="t1",
            type="type1",
        ),
        Puzzle(
            id="p2",
            fen="fen2",
            moves="m3 m4",
            rating=1100,
            rating_deviation=110,
            themes="t2",
            type="type2",
        ),
    ]
    repo.save_puzzles(puzzles)

    loaded = repo.get_puzzles()
    assert len(loaded) == 2
    assert loaded[0].id == "p1"

    uncompleted = repo.get_uncompleted_puzzles("agent1")
    assert len(uncompleted) == 2


def test_sqlite_game_and_move_ops(repo: SQLiteRepository) -> None:
    """
    Test creating games and saving moves.
    Why: This is the audit log of the evaluation. Storing every move (including illegal ones)
    is critical for analyzing model behavior and debugging "why did it fail?".
    """
    repo.save_agent(AgentData(name="agent1", is_reasoning=False, is_random=False))
    repo.save_puzzles(
        [
            Puzzle(
                id="p1",
                fen="fen1",
                moves="m1 m2",
                rating=1000,
                rating_deviation=100,
                themes="t1",
                type="type1",
            )
        ]
    )

    game_id = repo.create_game("p1", "agent1")
    assert game_id == 1

    move = MoveRecord(fen="fen1", expected_move="m1", actual_move="m1", is_illegal=False)
    repo.save_move(game_id, move)

    # Check if move was saved
    cursor = repo.conn.execute("SELECT * FROM move WHERE game_id = ?", (game_id,))
    row = cursor.fetchone()
    assert row["move"] == "m1"
    assert row["illegal_move"] == 0


def test_sqlite_benchmark_ops(repo: SQLiteRepository) -> None:
    """
    Test saving benchmark results (rating updates).
    Why: This stores the "final score" of an evaluation session. These records are used
    to plot rating trends over time, which is the main output of the library.
    """
    repo.save_agent(AgentData(name="agent1", is_reasoning=False, is_random=False))
    repo.save_puzzles(
        [
            Puzzle(
                id="p1",
                fen="fen1",
                moves="m1 m2",
                rating=1000,
                rating_deviation=100,
                themes="t1",
                type="type1",
            )
        ]
    )
    game_id = repo.create_game("p1", "agent1")

    repo.save_benchmark(game_id, 1600.0, 300.0, 0.05)

    # Verify agent cache update
    agent = repo.get_agent("agent1")
    assert agent is not None
    assert agent.rating == 1600.0
    assert agent.rd == 300.0
    assert agent.volatility == 0.05

    # Verify benchmark entry
    last = repo.get_last_benchmark("agent1")
    assert last == (1600.0, 300.0, 0.05)
