import os
import sqlite3
import pandas as pd
import logging
import traceback
from typing import Optional, Tuple

# ---------------------------
# Module: Base de données (SQLite)
# ---------------------------
class DatabaseManager:
    _instance = None

    # Singleton pattern to ensure only one instance of DatabaseManager
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: str = os.getenv("DB_PATH", "data/storage.db")):
        if self._initialized and db_path == self.db_path:
            return # Do not reinitialize if instance already exists
        
        self.logger = logging.getLogger('chess_benchmark.database')
        self.db_path = db_path
        self.logger.info(f"Initializing database at {self.db_path}")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()

            # Enable foreign key constraints
            self.cursor.execute("PRAGMA foreign_keys = ON;")
            # Enable WAL mode for better concurrency
            self.cursor.execute("PRAGMA journal_mode=WAL;")

            self.create_tables()
            self._initialized = True
            self.logger.info("Database initialized successfully")
        except Exception as e:
            self.logger.critical(f"Database initialization failed: {e}")
            self.logger.critical(traceback.format_exc())
            raise

    def create_tables(self):
        """
        Create the necessary tables in the database.
        """
        # Create puzzle table
        self.cursor.execute('''
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
        ''')
        
        # Create agent table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent (
                name TEXT PRIMARY KEY,
                reasoning BOOLEAN,
                random BOOLEAN DEFAULT 0
            )
        ''')
        
        # Create game table 
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS game (
                id INTEGER PRIMARY KEY,
                puzzle_id TEXT REFERENCES puzzle(id) ON DELETE CASCADE,
                agent_name TEXT REFERENCES agent(name) ON DELETE CASCADE,
                date TEXT DEFAULT CURRENT_TIMESTAMP,
                failed BOOLEAN,
                UNIQUE(puzzle_id, agent_name)
            )
        ''')
        
        # Create move table to store all moves (both opponent and agent)
        self.cursor.execute('''
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
        ''')

        # Add a partial unique index to prevent duplicate legal moves
        # This ensures that the combination of game_id, fen, and move is unique ONLY when illegal_move is 0 (False)
        self.cursor.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_legal_move 
            ON move (game_id, fen, move) 
            WHERE illegal_move = 0; 
        ''')
        
        # Create benchmark table 
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS benchmark (
                id INTEGER PRIMARY KEY,
                game_id INTEGER REFERENCES game(id) ON DELETE CASCADE,
                agent_rating INTEGER,
                agent_deviation INTEGER,
                agent_volatility INTEGER,
                UNIQUE(game_id)
            )
        ''')
        
        self.conn.commit()
        self.logger.info("Database tables created/verified")

    def insert_puzzles(self, puzzles_df: pd.DataFrame) -> pd.DataFrame:
        """
        Insert the selected puzzles into the database.
        """
        # Convert DataFrame to list of tuples
        puzzles = puzzles_df.to_records(index=False).tolist()
        
        # Insert puzzles into the database
        self.cursor.executemany('''
            INSERT OR IGNORE INTO puzzle (id, fen, moves, rating, rating_deviation, popularity, nb_plays, themes, game_url, opening_tags, type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', puzzles)
        
        self.conn.commit()
        return self.get_puzzles()

    def create_agent(self, agent_name: str, reasoning: bool, random: bool = False):
        """
        Create a new agent entry in the database.
        """
        self.cursor.execute(
            "INSERT OR IGNORE INTO agent (name, reasoning, random) VALUES (?, ?, ?)",
            (agent_name, reasoning, random)
        )
        self.conn.commit()

    def create_game(self, puzzle_id: str, agent_name: str) -> int:
        """
        Create a new game entry in the database or retrieve the existing one.
        Returns the ID of the game.
        """
        try:
            # Attempt to insert the game, ignoring if it already exists
            self.cursor.execute(
                "INSERT OR IGNORE INTO game (puzzle_id, agent_name) VALUES (?, ?)",
                (puzzle_id, agent_name)
            )
            self.conn.commit()

            # Whether inserted or ignored, fetch the actual game ID
            self.cursor.execute(
                "SELECT id FROM game WHERE puzzle_id = ? AND agent_name = ?",
                (puzzle_id, agent_name)
            )
            result = self.cursor.fetchone()

            if result:
                game_id = result[0]
                return game_id
            else:
                # This should theoretically not happen if INSERT OR IGNORE worked correctly
                self.logger.error(f"Could not find game ID for puzzle {puzzle_id} and agent {agent_name} after INSERT OR IGNORE.")
                raise ValueError("Failed to create or find game entry.")

        except sqlite3.Error as e:
            self.logger.error(f"Database error in create_game for puzzle {puzzle_id}, agent {agent_name}: {e}")
            self.logger.error(traceback.format_exc())
            self.conn.rollback() # Rollback in case of other errors
            raise

    def save_move(self, game_id: int, fen: str, correct_move: str, move: str, prompt_tokens: int, completion_tokens: int, illegal_move: bool):
        """
        Save the moves made by the agent during a game.
        """
        self.cursor.execute(
            "INSERT INTO move (game_id, fen, correct_move, move, prompt_tokens, completion_tokens, illegal_move) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (game_id, fen, correct_move, move, prompt_tokens, completion_tokens, illegal_move)
        )
        self.conn.commit()

    def save_benchmarks(self, game_id: int, agent_rating: int, agent_deviation: int, agent_volatility: int):
        """
        Save the benchmarks for a game.
        """
        self.cursor.execute(
            "INSERT INTO benchmark (game_id, agent_rating, agent_deviation, agent_volatility) VALUES (?, ?, ?, ?)",
            (game_id, agent_rating, agent_deviation, agent_volatility)
        )
        self.conn.commit()
    
    # update the game table with the puzzle outcome (failed: True/False)
    def update_game_result(self, game_id: int, failed: bool):
        self.cursor.execute(
            "UPDATE game SET failed = ?, date = CURRENT_TIMESTAMP WHERE id = ?",
            (failed, game_id)
        )
        self.conn.commit()
    
    # Get puzzles that have not been completed by a specific agent
    def get_uncompleted_puzzles_for_agent(self, agent_name: str) -> Optional[pd.DataFrame]:
        """
        Get puzzles that have not been completed by a specific agent.
        """
        # Get puzzles that have not been completed by the agent
        query = '''
            SELECT p.*
            FROM puzzle p
            LEFT JOIN game g ON p.id = g.puzzle_id AND g.agent_name = ?
            WHERE g.id IS NULL OR g.failed IS NULL
        '''
        self.cursor.execute(query, (agent_name,))
        rows = self.cursor.fetchall()

        if not rows:
            self.logger.info(f"No uncompleted puzzles found for agent {agent_name}.")
            return None

        # Convert rows to DataFrame
        columns = [col[0] for col in self.cursor.description]
        # Delete the moves for the uncompleted puzzles
        query = '''
            DELETE FROM move
            WHERE game_id IN (
                SELECT g.id
                FROM game g
                WHERE g.agent_name = ? AND g.failed IS NULL
            )
        '''
        self.cursor.execute(query, (agent_name,))
        self.conn.commit()

        return pd.DataFrame(rows, columns=columns)
    
    def get_puzzles(self) -> Optional[pd.DataFrame]:
        """
        Get all puzzles from the database.
        """
        self.cursor.execute("SELECT * FROM puzzle")
        rows = self.cursor.fetchall()
        
        if not rows:
            return None
        
        columns = [column[0] for column in self.cursor.description]
        return pd.DataFrame(rows, columns=columns)
    
    def get_last_benchmarks(self, agent_name: str) -> Optional[tuple]:
        """
        Get the most recent benchmarks for a given agent from the database.
        """
        query = '''
            SELECT b.agent_rating, b.agent_deviation, b.agent_volatility
            FROM benchmark b
            LEFT JOIN game g ON g.id = b.game_id
            WHERE g.agent_name = ?
            ORDER BY b.id DESC LIMIT 1
        '''
        self.cursor.execute(query, (agent_name,))
        row = self.cursor.fetchone()
        return row if row else None
    
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
                ROW_NUMBER() OVER(PARTITION BY g.agent_name ORDER BY b.id) as evaluation_index
            FROM benchmark b
            LEFT JOIN game g ON g.id = b.game_id
            ORDER BY b.id
        """
        df = pd.read_sql_query(query, self.conn, parse_dates=["date"])
        return df
    
    def get_illegal_moves_data(self) -> pd.DataFrame:
        """
        Get the number of moves and the number of illegal moves for each model (non-random agents).
        Returns columns: agent_name, total_moves, illegal_moves_count.
        """
        query = """
            SELECT a.name as agent_name,
                COUNT(m.id) as total_moves,
                COALESCE(SUM(CASE WHEN m.illegal_move = 1 THEN 1 ELSE 0 END), 0) as illegal_moves_count
            FROM agent a
            JOIN game g ON a.name = g.agent_name
            JOIN move m ON g.id = m.game_id
            WHERE a.random = 0
            GROUP BY a.name
        """
        df = pd.read_sql_query(query, self.conn)
        return df
    
    def get_final_ratings_data(self) -> pd.DataFrame:
        """
        Get each agent's most recent rating and rating deviation using the latest benchmark id.
        Returns columns: agent_name, agent_rating, agent_deviation.
        """
        query = """
            SELECT m.name AS agent_name,
                b.agent_rating,
                b.agent_deviation
            FROM agent m
            JOIN game g ON g.agent_name = m.name
            JOIN benchmark b ON b.game_id = g.id
            WHERE b.id = (
                SELECT MAX(b2.id)
                FROM benchmark b2
                JOIN game g2 ON b2.game_id = g2.id
                WHERE g2.agent_name = m.name
            )
        """
        return pd.read_sql_query(query, self.conn)

    def get_solutionary_agent_moves(self) -> pd.DataFrame:
        """
        Retrieve the puzzle solutionary moves and corresponding legal moves for each agent.
        Returns columns: agent_name, moves, agent_moves.
        """
        query = """
            SELECT g.agent_name, p.moves, group_concat(m.move, ' ') as agent_moves
            FROM game g
            JOIN puzzle p ON g.puzzle_id = p.id
            LEFT JOIN move m ON m.game_id = g.id
            WHERE m.illegal_move = 0
            GROUP BY g.id
        """
        return pd.read_sql_query(query, self.conn)
    
    
    def get_weighted_puzzle_rating(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculate the weighted average rating and rating deviation from the puzzles table.
        Returns a tuple (weighted_rating, weighted_rd).
        """
        self.cursor.execute("""
            SELECT 
                SUM(rating * popularity) * 1.0 / SUM(popularity) as weighted_rating,
                SUM(rating_deviation * popularity) * 1.0 / SUM(popularity) as weighted_rd
            FROM puzzle
            WHERE rating IS NOT NULL AND rating_deviation IS NOT NULL AND popularity > 0
        """)
        row = self.cursor.fetchone()
        if row and row[0] is not None:
            return row[0], row[1]
        else:
            return None, None

    def _get_puzzle_outcomes(self, group_by_agent=False) -> pd.DataFrame:
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
        Retrieve solutionnary puzzle moves data joined with corresponding legal moves for each agent.
        Returns columns: agent_name, themes, puzzle_rating, puzzle_deviation, moves, agent_moves.
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
            LEFT JOIN move m ON m.game_id = g.id
            WHERE m.illegal_move = 0
            GROUP BY g.id
        """
        return pd.read_sql_query(query, self.conn)