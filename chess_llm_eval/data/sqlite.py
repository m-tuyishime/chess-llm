import contextlib
import logging
import os
import sqlite3
from datetime import datetime
from typing import Any

import pandas as pd

from chess_llm_eval.data.models import AgentData, AgentRanking, Game, MoveRecord, Puzzle

# We don't inherit from GameRepository at runtime for perf/simplicity, but we match the protocol.
# Mypy will check the compatibility.

logger = logging.getLogger(__name__)


class SQLiteRepository:
    """SQLite implementation of GameRepository."""

    def __init__(self, db_path: str = "data/storage.db", immutable: bool = False):
        self.db_path = db_path
        self.immutable = immutable

        if immutable:
            # Use immutable mode for read-only filesystems (e.g., Vercel)
            # This skips all locking/journaling for maximum performance
            absolute_path = os.path.abspath(db_path)
            uri = f"file:{absolute_path}?immutable=1"
            logger.debug(f"Opening database in immutable mode: {uri}")
            self.conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            # Skip table creation in immutable mode - database is pre-populated
        else:
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self._create_tables()

    def _create_tables(self) -> None:
        cursor = self.conn.cursor()

        # Puzzle
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS puzzle (
                id TEXT PRIMARY KEY,
                fen TEXT,
                moves TEXT,
                rating INTEGER,
                rating_deviation INTEGER,
                popularity INTEGER,
                nb_plays INTEGER,
                themes TEXT,
                game_url TEXT,
                opening_tags TEXT,
                type TEXT
            )
        """)

        # Agent
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent (
                name TEXT PRIMARY KEY,
                reasoning BOOLEAN,
                random BOOLEAN DEFAULT 0,
                rating REAL DEFAULT 1500.0,
                rd REAL DEFAULT 350.0,
                volatility REAL DEFAULT 0.06
            )
        """)
        # Note: Added rating/rd/vol directly to agent table for simplicity/cache,
        # but historical benchmarks are still in 'benchmark' table.
        # Wait, the original schema had 'benchmark' separately. I should respect provided schema
        # but maybe add cached fields to 'agent' for faster 'get_agent'.
        # Actually my `models.py` has `AgentData` with rating.
        # I'll stick to original schema for `benchmark` logic to avoid
        # migration headaches if possible,
        # or just add columns if they don't exist.

        with contextlib.suppress(sqlite3.OperationalError):
            cursor.execute("ALTER TABLE agent ADD COLUMN rating REAL DEFAULT 1500.0")
        with contextlib.suppress(sqlite3.OperationalError):
            cursor.execute("ALTER TABLE agent ADD COLUMN rd REAL DEFAULT 350.0")
        with contextlib.suppress(sqlite3.OperationalError):
            cursor.execute("ALTER TABLE agent ADD COLUMN volatility REAL DEFAULT 0.06")

        # Game
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS game (
                id INTEGER PRIMARY KEY,
                puzzle_id TEXT REFERENCES puzzle(id) ON DELETE CASCADE,
                agent_name TEXT REFERENCES agent(name) ON DELETE CASCADE,
                date TEXT DEFAULT CURRENT_TIMESTAMP,
                failed BOOLEAN,
                UNIQUE(puzzle_id, agent_name)
            )
        """)

        # Move
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS move (
                id INTEGER PRIMARY KEY,
                game_id INTEGER REFERENCES game(id) ON DELETE CASCADE,
                fen TEXT,
                correct_move TEXT,
                move TEXT,
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                illegal_move BOOLEAN
            )
        """)

        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_legal_move
            ON move (game_id, fen, move)
            WHERE illegal_move = 0;
        """)

        # Benchmark
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS benchmark (
                id INTEGER PRIMARY KEY,
                game_id INTEGER REFERENCES game(id) ON DELETE CASCADE,
                agent_rating REAL,
                agent_deviation REAL,
                agent_volatility REAL,
                UNIQUE(game_id)
            )
        """)

        # Indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_game_agent_name ON game(agent_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_game_puzzle_id ON game(puzzle_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_move_game_id ON move(game_id)")

        self.conn.commit()

    # --- Puzzle Management ---

    def get_puzzles(self, limit: int | None = None) -> list[Puzzle]:
        query = "SELECT * FROM puzzle"
        params = []
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        cursor = self.conn.execute(query, tuple(params))
        return [self._map_puzzle(row) for row in cursor.fetchall()]

    def get_puzzle(self, puzzle_id: str) -> Puzzle | None:
        cursor = self.conn.execute("SELECT * FROM puzzle WHERE id = ?", (puzzle_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._map_puzzle(row)

    def get_uncompleted_puzzles(self, agent_name: str, limit: int | None = None) -> list[Puzzle]:
        query = """
            SELECT p.* FROM puzzle p
            LEFT JOIN game g ON p.id = g.puzzle_id AND g.agent_name = ?
            WHERE g.id IS NULL
        """
        params: list[Any] = [agent_name]
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        cursor = self.conn.execute(query, tuple(params))
        return [self._map_puzzle(row) for row in cursor.fetchall()]

    def save_puzzles(self, puzzles: list[Puzzle]) -> None:
        data = [
            (
                p.id,
                p.fen,
                p.moves,
                p.rating,
                p.rating_deviation,
                p.popularity,
                p.nb_plays,
                p.themes,
                p.game_url,
                p.opening_tags,
                p.type,
            )
            for p in puzzles
        ]
        self.conn.executemany(
            """
            INSERT OR REPLACE INTO puzzle
            (id, fen, moves, rating, rating_deviation, popularity, nb_plays,
             themes, game_url, opening_tags, type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            data,
        )
        self.conn.commit()

    def _map_puzzle(self, row: sqlite3.Row) -> Puzzle:
        return Puzzle(
            id=row["id"],
            fen=row["fen"],
            moves=row["moves"],
            rating=row["rating"],
            rating_deviation=row["rating_deviation"],
            popularity=row["popularity"],
            nb_plays=row["nb_plays"],
            themes=row["themes"],
            game_url=row["game_url"],
            opening_tags=row["opening_tags"],
            type=row["type"],
        )

    # --- Agent Management ---

    def get_agent(self, name: str) -> AgentData | None:
        cursor = self.conn.execute("SELECT * FROM agent WHERE name = ?", (name,))
        row = cursor.fetchone()
        if not row:
            return None

        # Try to get latest benchmark if columns are not populated or just rely on columns
        # For robustness, we will trust the columns if we are updating them.
        # But if we rely on benchmark table, we need a join.
        # Let's do a join to be safe on existing data without migration.

        # Actually, let's just get the latest benchmark and fill defaults if missing
        bench_cursor = self.conn.execute(
            """
            SELECT b.agent_rating, b.agent_deviation, b.agent_volatility
            FROM benchmark b
            JOIN game g ON b.game_id = g.id
            WHERE g.agent_name = ?
            ORDER BY g.date DESC LIMIT 1
        """,
            (name,),
        )
        bench_row = bench_cursor.fetchone()

        rating = bench_row["agent_rating"] if bench_row else row["rating"]
        rd = bench_row["agent_deviation"] if bench_row else row["rd"]
        vol = bench_row["agent_volatility"] if bench_row else row["volatility"]

        return AgentData(
            name=row["name"],
            is_reasoning=bool(row["reasoning"]),
            is_random=bool(row["random"]),
            rating=float(rating) if rating is not None else 1500.0,
            rd=float(rd) if rd is not None else 350.0,
            volatility=float(vol) if vol is not None else 0.06,
        )

    def save_agent(self, agent: AgentData) -> None:
        self.conn.execute(
            """
            INSERT INTO agent (name, reasoning, random, rating, rd, volatility)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                rating=excluded.rating,
                rd=excluded.rd,
                volatility=excluded.volatility
        """,
            (
                agent.name,
                agent.is_reasoning,
                agent.is_random,
                agent.rating,
                agent.rd,
                agent.volatility,
            ),
        )
        self.conn.commit()

    def get_all_agents(self) -> list[AgentData]:
        # Fetch all agents in one go with their latest benchmark stats
        query = """
            SELECT
                a.*,
                b.agent_rating as last_rating,
                b.agent_deviation as last_rd,
                b.agent_volatility as last_vol
            FROM agent a
            LEFT JOIN (
                SELECT g.agent_name, b.*
                FROM benchmark b
                JOIN game g ON b.game_id = g.id
                WHERE b.id IN (
                    SELECT MAX(b2.id)
                    FROM benchmark b2
                    JOIN game g2 ON b2.game_id = g2.id
                    GROUP BY g2.agent_name
                )
            ) b ON a.name = b.agent_name
        """
        cursor = self.conn.execute(query)
        agents = []
        for row in cursor.fetchall():
            rating = row["last_rating"] if row["last_rating"] is not None else row["rating"]
            rd = row["last_rd"] if row["last_rd"] is not None else row["rd"]
            vol = row["last_vol"] if row["last_vol"] is not None else row["volatility"]

            agents.append(
                AgentData(
                    name=row["name"],
                    is_reasoning=bool(row["reasoning"]),
                    is_random=bool(row["random"]),
                    rating=float(rating) if rating is not None else 1500.0,
                    rd=float(rd) if rd is not None else 350.0,
                    volatility=float(vol) if vol is not None else 0.06,
                )
            )
        return agents

    # --- Game Management ---

    def create_game(self, puzzle_id: str, agent_name: str) -> int:
        cursor = self.conn.execute(
            "INSERT INTO game (puzzle_id, agent_name, failed) VALUES (?, ?, ?)",
            (
                puzzle_id,
                agent_name,
                False,
            ),  # Assume success initially? NO, failed=False means "not failed yet".
        )
        self.conn.commit()
        return cursor.lastrowid or 0

    def update_game_result(self, game_id: int, failed: bool) -> None:
        self.conn.execute("UPDATE game SET failed = ? WHERE id = ?", (failed, game_id))
        self.conn.commit()

    def save_move(self, game_id: int, move: MoveRecord) -> None:
        self.conn.execute(
            """
            INSERT INTO move (
                game_id, fen, correct_move, move, prompt_tokens, completion_tokens, illegal_move
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                game_id,
                move.fen,
                move.expected_move,
                move.actual_move,
                move.prompt_tokens,
                move.completion_tokens,
                move.is_illegal,
            ),
        )
        self.conn.commit()

    # --- Benchmarks ---

    def save_benchmark(self, game_id: int, rating: float, rd: float, volatility: float) -> None:
        self.conn.execute(
            """
            INSERT INTO benchmark (game_id, agent_rating, agent_deviation, agent_volatility)
            VALUES (?, ?, ?, ?)
        """,
            (game_id, rating, rd, volatility),
        )

        # Also update agent table cache
        # We need agent name. We can get it from game_id via join or just trust caller.
        # But helper method is better.
        # Let's just do a subquery or separate update.
        self.conn.execute(
            """
            UPDATE agent
            SET rating=?, rd=?, volatility=?
            WHERE name = (SELECT agent_name FROM game WHERE id=?)
        """,
            (rating, rd, volatility, game_id),
        )
        self.conn.commit()

    def get_last_benchmark(self, agent_name: str) -> tuple[float, float, float] | None:
        # Redundant if get_agent does this, but good for protocol
        agent = self.get_agent(agent_name)
        if agent:
            return (agent.rating, agent.rd, agent.volatility)
        return None

    def get_leaderboard(self) -> list[AgentRanking]:
        # Get all agents and stats in a single query with efficient grouping
        query = """
            SELECT
                a.name,
                a.rating as current_rating,
                a.rd as current_rd,
                COUNT(g.id) as total_games,
                SUM(CASE WHEN g.failed = 0 THEN 1 ELSE 0 END) as wins
            FROM agent a
            LEFT JOIN game g ON a.name = g.agent_name
            GROUP BY a.name
        """
        cursor = self.conn.execute(query)
        rankings = []

        for row in cursor.fetchall():
            total = row["total_games"]
            wins = row["wins"] if row["wins"] else 0
            win_rate = (wins / total) if total > 0 else 0.0

            rankings.append(
                AgentRanking(
                    name=row["name"],
                    rating=row["current_rating"],
                    rd=row["current_rd"],
                    win_rate=win_rate,
                    games_played=total,
                )
            )

        rankings.sort(key=lambda x: x.rating, reverse=True)
        return rankings

    def get_game(self, game_id: int) -> Game | None:
        cursor = self.conn.execute(
            """
            SELECT g.*, p.type as puzzle_type
            FROM game g
            JOIN puzzle p ON g.puzzle_id = p.id
            WHERE g.id = ?
        """,
            (game_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        # Get moves
        move_cursor = self.conn.execute(
            "SELECT * FROM move WHERE game_id = ? ORDER BY id", (game_id,)
        )
        moves = [self._map_move(m) for m in move_cursor.fetchall()]

        date_str = row["date"].replace(" ", "T") if row["date"] else datetime.now().isoformat()
        try:
            date_obj = datetime.fromisoformat(date_str)
        except ValueError:
            # Fallback if format is unexpected
            date_obj = datetime.now()

        return Game(
            id=row["id"],
            puzzle_id=row["puzzle_id"],
            puzzle_type=row["puzzle_type"],
            agent_name=row["agent_name"],
            failed=bool(row["failed"]),
            date=date_obj,
            moves=moves,
            move_count=len(moves),
        )

    def get_agent_games(self, agent_name: str) -> list[Game]:
        # Efficiently fetch games and move counts without loading all moves
        cursor = self.conn.execute(
            """
            SELECT g.*, p.type as puzzle_type, COUNT(m.id) as move_count
            FROM game g
            JOIN puzzle p ON g.puzzle_id = p.id
            LEFT JOIN move m ON g.id = m.game_id
            WHERE g.agent_name = ?
            GROUP BY g.id
            ORDER BY g.date DESC
        """,
            (agent_name,),
        )

        games = []
        for row in cursor.fetchall():
            date_str = row["date"].replace(" ", "T") if row["date"] else datetime.now().isoformat()
            try:
                date_obj = datetime.fromisoformat(date_str)
            except ValueError:
                date_obj = datetime.now()

            games.append(
                Game(
                    id=row["id"],
                    puzzle_id=row["puzzle_id"],
                    puzzle_type=row["puzzle_type"],
                    agent_name=row["agent_name"],
                    failed=bool(row["failed"]),
                    date=date_obj,
                    moves=[],  # Don't load moves for summary list
                    move_count=row["move_count"],
                )
            )
        return games

    def _map_move(self, row: sqlite3.Row) -> MoveRecord:
        return MoveRecord(
            id=row["id"],
            game_id=row["game_id"],
            fen=row["fen"],
            expected_move=row["correct_move"],
            actual_move=row["move"],
            is_illegal=bool(row["illegal_move"]),
            prompt_tokens=row["prompt_tokens"] or 0,
            completion_tokens=row["completion_tokens"] or 0,
        )

    # --- Reporting / Analysis Methods (returning Pandas DataFrames) ---

    def get_benchmark_data(self) -> pd.DataFrame:
        """
        Get all benchmark data from the database ordered by date.
        Returns columns: agent_name, agent_rating, agent_deviation, agent_volatility,
        and evaluation_index which is the sequential number of evaluations for each agent.
        """
        query = """
            SELECT
                g.agent_name,
                b.agent_rating,
                b.agent_deviation,
                b.agent_volatility,
                g.date,
                ROW_NUMBER() OVER(PARTITION BY g.agent_name ORDER BY b.id) as evaluation_index
            FROM benchmark b
            LEFT JOIN game g ON g.id = b.game_id
            ORDER BY b.id
        """
        return pd.read_sql_query(query, self.conn, parse_dates=["date"])

    def get_puzzle_outcome_data(self) -> pd.DataFrame:
        """
        Retrieve puzzle outcomes grouped by puzzle type.
        Returns columns: type, successes, failures.
        """
        return self._get_puzzle_outcomes(group_by_agent=False)

    def get_puzzle_outcomes_by_agent_data(self) -> pd.DataFrame:
        """
        Retrieve puzzle outcomes grouped by agent and puzzle type.
        Returns columns: agent_name, type, successes, failures.
        """
        return self._get_puzzle_outcomes(group_by_agent=True)

    def _get_puzzle_outcomes(self, group_by_agent: bool = False) -> pd.DataFrame:
        """
        Helper function to get puzzle outcome data with optional grouping by agent.
        A puzzle is considered failed if the game.failed field is True.
        """
        group_cols = "g.agent_name, p.type" if group_by_agent else "p.type"

        query = f"""
            SELECT {group_cols},
                SUM(CASE WHEN g.failed = 0 THEN 1 ELSE 0 END) as successes,
                SUM(CASE WHEN g.failed = 1 THEN 1 ELSE 0 END) as failures
            FROM game g
            JOIN puzzle p ON g.puzzle_id = p.id
            GROUP BY {group_cols}
        """
        return pd.read_sql_query(query, self.conn)

    def get_illegal_moves_data(self) -> pd.DataFrame:
        """
        Get the number of moves and the number of illegal moves for each model (non-random agents).
        Returns columns: agent_name, total_moves, illegal_moves_count.
        """
        query = """
            SELECT a.name as agent_name,
                COUNT(m.id) as total_moves,
                COALESCE(
                    SUM(CASE WHEN m.illegal_move = 1 THEN 1 ELSE 0 END), 0
                ) as illegal_moves_count
            FROM agent a
            JOIN game g ON a.name = g.agent_name
            JOIN move m ON g.id = m.game_id
            WHERE a.random = 0
            GROUP BY a.name
        """
        return pd.read_sql_query(query, self.conn)

    def get_final_ratings_data(self) -> pd.DataFrame:
        """
        Get each agent's most recent rating and rating deviation using the cached values
        in the agent table (maintained by save_benchmark).
        Returns columns: agent_name, agent_rating, agent_deviation.
        """
        query = """
            SELECT
                name AS agent_name,

                rating AS agent_rating,
                rd AS agent_deviation
            FROM agent
        """
        return pd.read_sql_query(query, self.conn)

    def get_weighted_puzzle_rating(self) -> tuple[float | None, float | None]:
        """
        Calculate the weighted average rating and rating deviation from the puzzles table.
        Returns a tuple (weighted_rating, weighted_rd).
        """
        cursor = self.conn.execute("""
            SELECT
                SUM(rating * popularity) * 1.0 / SUM(popularity) as weighted_rating,
                SUM(rating_deviation * popularity) * 1.0 / SUM(popularity) as weighted_rd
            FROM puzzle
            WHERE rating IS NOT NULL AND rating_deviation IS NOT NULL AND popularity > 0
        """)
        row = cursor.fetchone()
        if row and row["weighted_rating"] is not None:
            return row["weighted_rating"], row["weighted_rd"]
        else:
            return None, None

    def get_solutionary_agent_moves(self) -> pd.DataFrame:
        """
        Retrieve the puzzle solutionary moves and corresponding legal moves for each agent.
        Returns columns: agent_name, moves, agent_moves.
        """
        query = """
            SELECT g.agent_name, p.moves, group_concat(m.move, ' ') as agent_moves
            FROM game g
            JOIN puzzle p ON g.puzzle_id = p.id
            LEFT JOIN (SELECT * FROM move ORDER BY id) m ON m.game_id = g.id
            WHERE m.illegal_move = 0
            GROUP BY g.id
        """
        return pd.read_sql_query(query, self.conn)

    def get_token_usage_per_move_data(self) -> pd.DataFrame:
        """
        Get average token usage per move for each agent.
        Excludes agents that have token usage of 0 for both prompt and completion.
        Returns columns: agent_name, avg_prompt_tokens, avg_completion_tokens
        """
        query = """
            SELECT g.agent_name,
                   AVG(m.prompt_tokens) as avg_prompt_tokens,
                   AVG(m.completion_tokens) as avg_completion_tokens
            FROM move m
            JOIN game g ON m.game_id = g.id
            WHERE m.prompt_tokens IS NOT NULL AND m.completion_tokens IS NOT NULL
            GROUP BY g.agent_name
            HAVING AVG(m.prompt_tokens) > 0 AND AVG(m.completion_tokens) > 0
        """
        return pd.read_sql_query(query, self.conn)

    def get_token_usage_per_puzzle_data(self) -> pd.DataFrame:
        """
        Get average token usage per puzzle for each agent.
        Excludes agents that have token usage of 0 for both prompt and completion.
        Returns columns: agent_name, avg_puzzle_prompt_tokens, avg_puzzle_completion_tokens
        """
        query = """
            SELECT agent_name,
                   AVG(total_prompt) as avg_puzzle_prompt_tokens,
                   AVG(total_completion) as avg_puzzle_completion_tokens
            FROM (
                SELECT g.id as game_id,
                       g.agent_name as agent_name,
                       SUM(m.prompt_tokens) as total_prompt,
                       SUM(m.completion_tokens) as total_completion
                FROM game g
                JOIN move m ON m.game_id = g.id
                WHERE m.prompt_tokens IS NOT NULL AND m.completion_tokens IS NOT NULL
                GROUP BY g.id, g.agent_name
            ) puzzle_tokens
            GROUP BY agent_name
            HAVING AVG(total_prompt) > 0 AND AVG(total_completion) > 0
        """
        return pd.read_sql_query(query, self.conn)

    def get_solutionary_moves_data(self) -> pd.DataFrame:
        """
        Retrieve solutionnary puzzle moves data joined with
        corresponding legal moves for each agent.
        Returns columns: agent_name, themes, puzzle_rating,
        puzzle_deviation, moves, agent_moves.
        """
        query = """
            SELECT
                g.agent_name,
                p.type,
                p.rating as puzzle_rating,
                p.rating_deviation as puzzle_deviation,
                p.moves,
                group_concat(m.move, ' ') as agent_moves
            FROM game g
            JOIN puzzle p ON g.puzzle_id = p.id
            LEFT JOIN (SELECT * FROM move ORDER BY id) m ON m.game_id = g.id
            WHERE m.illegal_move = 0
            GROUP BY g.id
        """
        return pd.read_sql_query(query, self.conn)
