import logging
from typing import List, Optional
from aiolimiter import AsyncLimiter
import os
import pandas as pd
import matplotlib.pyplot as plt
import chess
import sqlite3
import aiohttp
import json
import re
import asyncio
import glicko2
import traceback
from datetime import datetime

# ---------------------------
# Module: Logging Configuration
# ---------------------------
def setup_logging():
    """Configure logging for the application"""
    log_dir = os.path.join(os.getcwd(), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f'chess_benchmark_{timestamp}.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    # Set specific logger levels
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    
    return logging.getLogger('chess_benchmark')

# Create the logger
logger = setup_logging()

# ---------------------------
# Module: OpenRouter
# ---------------------------
class OpenRouter:
    def __init__(self, api_key=os.getenv("OPENROUTER_API_KEY")):
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.logger = logging.getLogger('chess_benchmark.openrouter')

    async def send_request(self, body):
        """
        Send a request to the OpenRouter API.
        """
        model = body.get('model', 'unknown')
        timeout = aiohttp.ClientTimeout(total=60)
        self.logger.debug(f"Sending request to OpenRouter for model {model}")
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                self.logger.debug(f"Request payload: {json.dumps(body)[:500]}...")
                start_time = datetime.now()
                async with session.post(self.base_url, headers=self.headers, json=body) as response:
                    response_data = await response.json()
                    elapsed = (datetime.now() - start_time).total_seconds()
                    self.logger.debug(f"Received response in {elapsed:.2f}s")
        except asyncio.TimeoutError as e:
            self.logger.error(f"Request timed out for model {model}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error during API request for model {model}: {e}")
            self.logger.error(traceback.format_exc())
            return None
            
        if "choices" not in response_data:
            self.logger.error(f"Error in API response: {response_data}")
            return None

        content = response_data["choices"][0]["message"]["content"]
        pt = response_data.get("usage", {}).get("prompt_tokens", None)
        ct = response_data.get("usage", {}).get("completion_tokens", None)
        
        self.logger.debug(f"API response for {model}: {content[:100]}... (pt: {pt}, ct: {ct})")
        return {
            "content": content,
            "prompt_tokens": pt,
            "completion_tokens": ct
        }

# ---------------------------
# Module: LLM Models 
# ---------------------------
class LLMModel:
    def __init__(self, model_name:str, is_reasoning:bool, rate_per_minute:int, open_router=OpenRouter()):
        self.model_name = model_name
        self.is_reasoning = is_reasoning
        self.config = {
            "model": model_name,
            "messages": [], 
            "temperature": 0.0 # Set to 0.0 for deterministic responses
        }
        self.rate_per_minute = rate_per_minute
        self.open_router = open_router
        self.logger = logging.getLogger(f'chess_benchmark.model.{model_name}')
        self.logger.info(f"Initializing LLM model {model_name} (reasoning: {is_reasoning}, rpm: {rate_per_minute})")

        # Create the llm in the database
        DatabaseManager().create_model(model_name, is_reasoning)

        # Get the model's rating and deviation from the database
        last_benchmark = DatabaseManager().get_last_benchmarks(model_name)
        if last_benchmark:
            self.player = glicko2.Player(
                rating=last_benchmark[0],
                rd=last_benchmark[1],
                vol=last_benchmark[2]
            )
            self.logger.info(f"Loaded existing rating: {last_benchmark[0]} (RD: {last_benchmark[1]})")
        else:
            # If no benchmark exists, create a new player with default values
            self.player = glicko2.Player()
            self.logger.info(f"Creating new player with default rating: {self.player.rating}")

        # Create a limiter that allows 'rate_per_minute' requests per 60s
        self.limiter = AsyncLimiter(rate_per_minute, time_period=60)
        

    def parse_move(self, response:Optional[str]) -> Optional[str]:
        """
        Parse the move from the model's response. Returns None if no move is found.
        """
        if not response:
            self.logger.warning(f"Received empty response from model {self.model_name}")
            return ""
            
        match = re.search(r'(?:move:\s*)?([KQRBN]?(?:[a-h][1-8]|[a-h]?x[a-h][1-8])[+#]?)', response)
        if match:
            move = match.group(1)
            self.logger.debug(f"Parsed move: {move}")
            return move
        else:
            self.logger.warning(f"Failed to parse move from response: {response[:100]}...")
            return None

    def _create_base_messages(self, fen: str, legal_moves_san: List[str], color: str) -> List[dict]:
        """
        Create the base messages for a chess move prompt.
        """
        return [
            {
                "role": "system",
                "content": f"Here's a chess board FEN string: {fen}"
            },
            {
                "role": "system",
                "content": f"Here are the SAN legal moves for {color}: {', '.join(legal_moves_san)}"
            },
            {
                "role": "system",
                "content": f"What is the best move for {color}? Answer only with one move in SAN)"
            }
        ]

    async def _make_api_request(self, log_prefix: str = "") -> Optional[tuple]:
        """
        Make an API request with proper error handling and rate limiting.
        Returns a tuple of (move, prompt_tokens, completion_tokens) or None on error.
        """
        try:
            self.logger.debug(f"Waiting for rate limiter ({self.rate_per_minute} rpm)")
            async with self.limiter:
                response = await self.open_router.send_request(self.config)
                
            if not response:
                self.logger.error(f"{log_prefix}Failed to get response from API")
                return None, None, None
                
            move = self.parse_move(response["content"])
            pt = response.get("prompt_tokens", None)
            ct = response.get("completion_tokens", None)
            self.logger.info(f"{log_prefix}Model suggested move: {move} (pt: {pt}, ct: {ct})")
            return move, pt, ct
            
        except Exception as e:
            self.logger.error(f"{log_prefix}Error during API request: {e}")
            self.logger.error(traceback.format_exc())
            return None, None, None

    async def get_move(self, fen:str, legal_moves_san:List[str], color:str) -> Optional[tuple]:
        """
        Get the best move for a given board state.
        """
        self.logger.debug(f"Getting move for position: {fen}")
        self.logger.debug(f"Legal moves: {', '.join(legal_moves_san)}")
        
        # Create messages using the helper method
        base_messages = self._create_base_messages(fen, legal_moves_san, color)
        # Add the final prompt
        self.config["messages"] = base_messages + [
            {
                "role": "assistant",
                "content": "move: "
            }
        ]
        
        # Make the API request
        return await self._make_api_request()
    
    async def retry_move(self, failed_moves_san:List[str], fen:str, legal_moves_san:List[str], color:str) -> Optional[tuple]:
        """
        Reprompt the model for a move after a failed attempt.
        """
        self.logger.info(f"Retrying after {len(failed_moves_san)} illegal moves: {failed_moves_san}")
        
        # Create base messages using the helper method
        base_messages = self._create_base_messages(fen, legal_moves_san, color)
        
        # Create retry messages for each failed move
        retry_messages = []
        for move in failed_moves_san:
            retry_messages.extend([
                {
                    "role": "assistant",
                    "content": f"move: {move}"
                },
                {
                    "role": "system",
                    "content": "Invalid move. Please try again."
                }
            ])
        
        # Add final prompt message
        final_prompt = [
            {
                "role": "assistant",
                "content": "move: "
            }
        ]
        
        # Combine all messages together
        self.config["messages"] = base_messages + retry_messages + final_prompt
        
        # Make the API request with a prefix for logs
        return await self._make_api_request("Retry: ")

# ---------------------------
# Module: Sélection de puzzles
# ---------------------------
class PuzzleSelector:
    def __init__(self, csv_path):
        self.puzzles_df = pd.read_csv(csv_path)
        self.db_manager = DatabaseManager()

    def get_mate_puzzles(self) -> pd.DataFrame:
        """
        TODO: Return a DataFrame of mate puzzles.
        """
        # Example placeholder getting the first 10 rows 
        return self.puzzles_df.iloc[:10].copy()

    def get_tactic_puzzles(self) -> pd.DataFrame:
        """
        TODO: Return a DataFrame of tactic puzzles.
        """
        return self.puzzles_df.iloc[10:20].copy()

    def get_strategy_puzzles(self) -> pd.DataFrame:
        """
        TODO: Return a DataFrame of strategy puzzles.
        """
        return self.puzzles_df.iloc[20:30].copy()

    def get_endgame_puzzles(self) -> pd.DataFrame:
        """
        TODO: Return a DataFrame of endgame puzzles.
        """
        return self.puzzles_df.iloc[30:40].copy()

    def get_puzzles_for_model(self, llm: LLMModel) -> pd.DataFrame:
        # First, check if any puzzles exist at all
        all_puzzles = self.db_manager.get_puzzles()
        if all_puzzles is None:
            # Generate new puzzles selection using the existing logic
            mate_df = self.get_mate_puzzles()
            tactic_df = self.get_tactic_puzzles()
            strategy_df = self.get_strategy_puzzles()
            endgame_df = self.get_endgame_puzzles()
            
            if any(len(df) == 0 for df in [mate_df, tactic_df, strategy_df, endgame_df]):
                raise ValueError("One or more puzzle categories are empty.")
            
            num_cycles = min(len(mate_df), len(tactic_df), len(strategy_df), len(endgame_df))
            combined_rows = []
            for i in range(num_cycles):
                row = mate_df.iloc[i].copy()
                row["Type"] = "mate"
                combined_rows.append(row)
                
                row = tactic_df.iloc[i].copy()
                row["Type"] = "tactic"
                combined_rows.append(row)
                
                row = strategy_df.iloc[i].copy()
                row["Type"] = "strategy"
                combined_rows.append(row)
                
                row = endgame_df.iloc[i].copy()
                row["Type"] = "endgame"
                combined_rows.append(row)
            
            combined_df = pd.DataFrame(combined_rows)
            return self.db_manager.insert_puzzles(combined_df)
        else:
            # Return only puzzles that the model hasn't attempted
            model_puzzles = self.db_manager.get_uncompleted_puzzles_for_model(llm.model_name)
            if model_puzzles is None or model_puzzles.empty:
                print(f"All puzzles have already been evaluated by model {llm.model_name}. Exiting.")
                exit(0)
            return model_puzzles


# ---------------------------
# Module: Environnement de jeu 
# ---------------------------
class ChessEnvironment:
    def __init__(self, fen):
        self.board = chess.Board(fen)
        self.logger = logging.getLogger('chess_benchmark.environment')
        self.logger.debug(f"Created board with FEN: {fen}")

    def get_legal_moves(self) -> list:
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

# ---------------------------
# Module: Base de données (SQLite)
# ---------------------------
class DatabaseManager:
    _instance = None

    # Singleton pattern to ensure only one instance of DatabaseManager
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return # Do not reinitialize if already done
        
        self.logger = logging.getLogger('chess_benchmark.database')
        self.db_path = os.getenv("DB_PATH", "data/storage.db")
        self.logger.info(f"Initializing database at {self.db_path}")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
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
        # Enable foreign key constraints
        self.cursor.execute("PRAGMA foreign_keys = ON;")
        
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
        
        # Create model table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS model (
                name TEXT PRIMARY KEY,
                reasoning BOOLEAN
            )
        ''')
        
        # Create game table 
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS game (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                puzzle_id TEXT REFERENCES puzzle(id) ON DELETE CASCADE,
                model_name TEXT REFERENCES model(name) ON DELETE CASCADE,
                date TEXT DEFAULT (date('now'))
            )
        ''')
        
        # Create move table to store all moves (both opponent and model)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS move (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER REFERENCES game(id) ON DELETE CASCADE,
                fen TEXT,
                correct_move TEXT,
                move TEXT,
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                illegal_move BOOLEAN
            )
        ''')
        
        # Create benchmark table 
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS benchmark (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER REFERENCES game(id) ON DELETE CASCADE,
                model_rating INTEGER,
                model_deviation INTEGER,
                model_volatility INTEGER
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

    def create_model(self, model_name: str, reasoning: bool):
        """
        Create a new model entry in the database.
        """
        self.cursor.execute(
            "INSERT OR IGNORE INTO model (name, reasoning) VALUES (?, ?)",
            (model_name, reasoning)
        )
        self.conn.commit()

    def create_game(self, puzzle_id: str, model_name: str) -> int:
        """
        Create a new game entry in the database.
        Returns the ID of the new game.
        """
        self.cursor.execute(
            "INSERT INTO game (puzzle_id, model_name) VALUES (?, ?)",
            (puzzle_id, model_name)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def save_move(self, game_id: int, fen: str, correct_move: str, move: str, prompt_tokens: int, completion_tokens: int, illegal_move: bool):
        """
        Save the moves made by the model during a game.
        """
        self.cursor.execute(
            "INSERT INTO move (game_id, fen, correct_move, move, prompt_tokens, completion_tokens, illegal_move) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (game_id, fen, correct_move, move, prompt_tokens, completion_tokens, illegal_move)
        )
        self.conn.commit()

    def save_benchmarks(self, game_id: int, model_rating: int, model_deviation: int, model_volatility: int):
        """
        Save the benchmarks for a game.
        """
        self.cursor.execute(
            "INSERT INTO benchmark (game_id, model_rating, model_deviation, model_volatility) VALUES (?, ?, ?, ?)",
            (game_id, model_rating, model_deviation, model_volatility)
        )
        self.conn.commit()
    
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
    
    def get_last_benchmarks(self, model_name: str) -> Optional[tuple]:
        """
        Get the most recent benchmarks for a given model from the database.
        """
        query = '''
            SELECT b.model_rating, b.model_deviation, b.model_volatility
            FROM benchmark b
            JOIN game g ON b.game_id = g.id
            WHERE g.model_name = ?
            ORDER BY b.id DESC LIMIT 1
        '''
        self.cursor.execute(query, (model_name,))
        row = self.cursor.fetchone()
        return row if row else None
    
    def get_benchmark_data(self) -> pd.DataFrame:
        query = """
            SELECT g.model_name, b.id as benchmark_id, b.model_rating, g.date
            FROM benchmark b
            JOIN game g ON b.game_id = g.id
            ORDER BY g.date, b.id
        """
        df = pd.read_sql_query(query, self.conn, parse_dates=["date"])
        return df

    def get_illegal_moves_data(self) -> pd.DataFrame:
        query = """
            SELECT g.model_name, COUNT(m.id) as illegal_moves_count
            FROM move m
            JOIN game g ON m.game_id = g.id
            WHERE m.illegal_move = 1
            GROUP BY g.model_name
        """
        df = pd.read_sql_query(query, self.conn)
        return df
    
    def get_final_ratings_data(self) -> pd.DataFrame:
        """
        Get each model's most recent rating and rating deviation.
        This query uses correlated subqueries to fetch the final benchmark for each model.
        """
        query = """
            SELECT m.name AS model_name,
                   (SELECT b.model_rating
                    FROM game g
                    JOIN benchmark b ON g.id = b.game_id
                    WHERE g.model_name = m.name
                    ORDER BY b.id DESC LIMIT 1) AS model_rating,
                   (SELECT b.model_deviation
                    FROM game g
                    JOIN benchmark b ON g.id = b.game_id
                    WHERE g.model_name = m.name
                    ORDER BY b.id DESC LIMIT 1) AS model_deviation
            FROM model m
        """
        return pd.read_sql_query(query, self.conn)

    def get_moves_data(self) -> pd.DataFrame:
        """
        Retrieve game moves data joining game and puzzles.
        """
        query = """
            SELECT g.model_name, p.moves, group_concat(m.move, ' ') as model_moves
            FROM game g
            JOIN puzzle p ON g.puzzle_id = p.id
            LEFT JOIN move m ON m.game_id = g.id
            GROUP BY g.id
        """
        return pd.read_sql_query(query, self.conn)
    
    # New method: return puzzles that the given model hasn't seen yet
    def get_uncompleted_puzzles_for_model(self, model_name: str) -> Optional[pd.DataFrame]:
        # Modified query: exclude puzzles for which a game exists with matching move count.
        query = """
            SELECT *
            FROM puzzle p
            WHERE NOT EXISTS (
                SELECT 1
                FROM game g
                JOIN move m ON m.game_id = g.id
                WHERE g.model_name = ?
                  AND g.puzzle_id = p.id
                GROUP BY g.id
                HAVING COUNT(m.id) = (LENGTH(TRIM(p.moves)) - LENGTH(REPLACE(TRIM(p.moves), ' ', '')) + 1)
            )
        """
        self.cursor.execute(query, (model_name,))
        rows = self.cursor.fetchall()
        if not rows:
            return None
        columns = [col[0] for col in self.cursor.description]
        return pd.DataFrame(rows, columns=columns)
    
    # New method to get weighted puzzle rating and deviation
    def get_weighted_puzzle_rating(self) -> tuple:
        # Calculate weighted average rating and rating deviation from puzzles table
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

    def _get_puzzle_outcomes(self, group_by_model=False) -> pd.DataFrame:
        """
        Helper function to get puzzle outcome data with optional grouping by model.
        A puzzle is considered failed if any move doesn't match the correct move
        (excluding illegal moves).
        """
        group_cols = "g.model_name, p.type" if group_by_model else "p.type"
        
        query = f"""
            SELECT {group_cols},
                   SUM(CASE WHEN NOT EXISTS (
                       SELECT 1 FROM move m 
                       WHERE m.game_id = g.id 
                       AND m.move != m.correct_move 
                       AND m.illegal_move = 0
                   ) THEN 1 ELSE 0 END) as successes,
                   SUM(CASE WHEN EXISTS (
                       SELECT 1 FROM move m 
                       WHERE m.game_id = g.id 
                       AND m.move != m.correct_move 
                       AND m.illegal_move = 0
                   ) THEN 1 ELSE 0 END) as failures
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
        return self._get_puzzle_outcomes(group_by_model=False)
    
    def get_puzzle_outcomes_by_model_data(self) -> pd.DataFrame:
        """
        Retrieve puzzle outcomes grouped by model and puzzle type.
        Returns columns: model_name, type, successes, failures.
        """
        return self._get_puzzle_outcomes(group_by_model=True)

# ---------------------------
# Module: Module d'évaluation 
# ---------------------------
class Evaluator:
    def __init__(self, llm:LLMModel, puzzles_df:pd.DataFrame):
        self.llm = llm
        self.puzzles_df = puzzles_df
        self.db_manager = DatabaseManager()
        self.logger = logging.getLogger(f'chess_benchmark.evaluator.{llm.model_name}')
        self.logger.info(f"Initialized evaluator for model {llm.model_name} with {len(puzzles_df)} puzzles")

    def update_llm_rating(self, puzzle_ratings:List[int], puzzle_deviations:List[int], puzzle_wins:List[bool]):
        """
        Update the LLM's rating and deviation based on the results of the puzzles.
        """
        self.logger.debug(f"Updating rating: puzzle ratings={puzzle_ratings}, wins={puzzle_wins}")
        self.llm.player.update_player(puzzle_ratings, puzzle_deviations, puzzle_wins)
        new_rating = self.llm.player.rating
        new_rd = self.llm.player.rd
        new_vol = self.llm.player.vol
        
        self.logger.info(f"Updated rating: {new_rating} (RD: {new_rd})")
        return new_rating, new_rd, new_vol
    
    async def evaluate_puzzle(self, puzzle:pd.Series) -> Optional[tuple]:
        """
        Evaluate a single puzzle. On error, exit early; do not complete the puzzle.
        Returns (rating, deviation, volatility) if evaluated.
        """
        puzzle_id = puzzle.id
        puzzle_type = getattr(puzzle, 'type', getattr(puzzle, 'Type', 'unknown'))
        self.logger.info(f"Starting evaluation of puzzle {puzzle_id} (type: {puzzle_type})")
        
        try:
            db = self.db_manager
            fen = puzzle.fen
            solution = puzzle.moves.split(" ")
            puzzle_rating = puzzle.rating
            puzzle_deviation = puzzle.rating_deviation

            self.logger.debug(f"Puzzle {puzzle_id}: Initial FEN: {fen}")
            self.logger.debug(f"Puzzle {puzzle_id}: Solution moves: {solution}")

            game_id = db.create_game(puzzle_id, self.llm.model_name)
            self.logger.info(f"Created game_id {game_id} for puzzle {puzzle_id}")
            
            chess_env = ChessEnvironment(fen)
            failed_puzzle = False

            # Iterate through the moves of the solution in pairs (opponent's move, model's move)
# The number of moves in the solution should be always even
            for i in range(0, len(solution), 2):
                # Play the opponent's move
                try:
                    opponent_move = chess_env.uci_to_san(solution[i])
                    self.logger.debug(f"Puzzle {puzzle_id}: Opponent move {i//2+1}: {opponent_move}")
                    
                    # Get the new FEN after applying the opponent's move
                    fen = chess_env.apply_move(opponent_move)
                    # Save opponent move (always correct)
                    db.save_move(game_id, fen, opponent_move, opponent_move, 0, 0, False)
                except Exception as e:
                    self.logger.error(f"Failed to apply opponent move: {e}")
                    self.logger.error(traceback.format_exc())
                    failed_puzzle = True
                    break

                # Check if we're at the end of the solution
                if i+1 >= len(solution):
                    self.logger.warning(f"Puzzle {puzzle_id}: Odd number of moves in solution, ending after opponent's move")
                    break

                # Get the color of the side to move
                color = chess_env.get_turn_color()
                # Get the legal moves for the current position
                legal_moves_san = chess_env.get_legal_moves()
                # Get the expected move from the solution
                expected_move = chess_env.uci_to_san(solution[i+1])
                self.logger.debug(f"Puzzle {puzzle_id}: Expected model move: {expected_move}")
                
                # LLM generates a move
                move, prompt_tokens, completion_tokens = await self.llm.get_move(fen, legal_moves_san, color)

                if move is None:
                    self.logger.error(f"Puzzle {puzzle_id}: Model failed to generate move, exiting early")
                    # Exit this task early request error, leaving puzzle uncompleted
                    return None
                
                self.logger.info(f"Puzzle {puzzle_id}: Model move: {move} (expected: {expected_move})")
                
                # Store the illegal moves
                illegal_moves_san = []
                # Retry until a legal move is found or 5 illegal moves are stored
                while not chess_env.is_move_legal(move) and len(illegal_moves_san) < 5:
                    self.logger.warning(f"Puzzle {puzzle_id}: Illegal move {move}, retrying")
                    illegal_moves_san.append(move)
                    move, prompt_tokens, completion_tokens = await self.llm.retry_move(illegal_moves_san, fen, legal_moves_san, color)
                    if move is None:
                        self.logger.error(f"Puzzle {puzzle_id}: Model failed during retry, exiting early")
                        # Exit this task early request error, leaving puzzle uncompleted
                        return None
                    
                    # store the illegal move
                    db.save_move(game_id, fen, expected_move, move, prompt_tokens, completion_tokens, True)
                    self.logger.debug(f"Puzzle {puzzle_id}: Retry generated move: {move}")

                # If the move is still illegal after retries, mark the puzzle as failed (terminal move)
                if not chess_env.is_move_legal(move):
                    self.logger.warning(f"Puzzle {puzzle_id}: Move {move} still illegal after retries")
                    failed_puzzle = True
                    db.save_move(game_id, fen, expected_move, move, prompt_tokens, completion_tokens, False)
                    break

                # Apply the move to the board and get the new FEN
                try:
                    fen = chess_env.apply_move(move)
                    db.save_move(game_id, fen, expected_move, move, prompt_tokens, completion_tokens, False)
                except Exception as e:
                    self.logger.error(f"Failed to apply model move: {e}")
                    self.logger.error(traceback.format_exc())
                    failed_puzzle = True
                    break

                # If the move doesn't match the expected move, mark the puzzle as failed (terminal move)
                if move != expected_move:
                    self.logger.info(f"Puzzle {puzzle_id}: Move {move} doesn't match expected {expected_move}")
                    failed_puzzle = True
                    break

            # Update benchmarks based on outcome
            result = "SUCCESS" if not failed_puzzle else "FAILURE"
            self.logger.info(f"Puzzle {puzzle_id} evaluation complete: {result}")
            rating, deviation, volatility = self.update_llm_rating([puzzle_rating], [puzzle_deviation], [not failed_puzzle])
            db.save_benchmarks(game_id, rating, deviation, volatility)
            return (rating, deviation, volatility)
            
        except Exception as e:
            self.logger.error(f"Error evaluating puzzle {puzzle_id}: {e}")
            self.logger.error(traceback.format_exc())
            return None

    async def evaluate_all(self, target_deviation: int) -> None:
        """
        Evaluate all puzzles concurrently until target deviation is reached.
        """
        self.logger.info(f"Starting evaluation of {len(self.puzzles_df)} puzzles (target deviation: {target_deviation})")
        
        # Create tasks for all puzzles to run concurrently and keep track of puzzle IDs
        tasks = []
        task_to_puzzle_id = {}  # Dictionary to map tasks to their puzzle IDs
        
        for puzzle in self.puzzles_df.itertuples():
            task = asyncio.create_task(self.evaluate_puzzle(puzzle))
            tasks.append(task)
            task_to_puzzle_id[task] = puzzle.id
        
        self.logger.info(f"Created {len(tasks)} evaluation tasks")
        
        completed = 0
        for task in asyncio.as_completed(tasks):
            puzzle_id = task_to_puzzle_id.get(task, "unknown")
            
            try:
                result = await task
                completed += 1
                
                if result is None:
                    self.logger.warning(f"Puzzle {puzzle_id} returned None")
                    continue
                    
                _, deviation, _ = result
                self.logger.info(f"Completed {completed}/{len(tasks)} puzzles. Current deviation: {deviation}")
                
                if deviation < target_deviation:
                    self.logger.info(f"Target deviation {target_deviation} reached, canceling remaining tasks")
                    # Cancel any remaining tasks if target condition is met
                    canceled = 0
                    for pending in tasks:
                        if not pending.done():
                            pending.cancel()
                            canceled += 1
                    
                    self.logger.info(f"Canceled {canceled} remaining tasks")
                    break
                    
            except asyncio.CancelledError:
                self.logger.debug(f"Task for puzzle {puzzle_id} was canceled")
                continue
            except Exception as e:
                self.logger.error(f"Error in task for puzzle {puzzle_id}: {e}")
                self.logger.error(traceback.format_exc())
                continue
                
        self.logger.info(f"Evaluation complete: {completed}/{len(tasks)} puzzles evaluated")

# ---------------------------
# Module: Création de rapports
# ---------------------------
class ReportGenerator:
    def __init__(self, db_manager=DatabaseManager()):
        self.db_manager = db_manager

    def generate_model_rating_trends(self):
        """
        Generate a line plot showing the trend of model ratings over time.
        """
        df = self.db_manager.get_benchmark_data()
        if df.empty:
            print("No benchmark data available.")
            return

        plt.figure(figsize=(10, 6))
        for model_name, data in df.groupby("model_name"):
            data = data.sort_values("benchmark_id")
            plt.plot(data["benchmark_id"], data["model_rating"], label=model_name)
        plt.xlabel("Benchmark ID")
        plt.ylabel("Model Rating")
        plt.title("Model Rating Trends Over Time")
        plt.legend()
        plt.show()

    def generate_model_deviation_trends(self):
        # New method: generate a line plot of model deviations over time.
        query = """
            SELECT g.model_name, b.id as benchmark_id, b.model_deviation, g.date
            FROM benchmark b
            JOIN game g ON b.game_id = g.id
            ORDER BY g.date, b.id
        """
        df = pd.read_sql_query(query, self.db_manager.conn, parse_dates=["date"])
        if df.empty:
            print("No benchmark deviation data available.")
            return

        plt.figure(figsize=(10, 6))
        for model_name, data in df.groupby("model_name"):
            data = data.sort_values("benchmark_id")
            plt.plot(data["benchmark_id"], data["model_deviation"], label=model_name)
        plt.xlabel("Benchmark ID")
        plt.ylabel("Model Deviation")
        plt.title("Model Deviation Trends Over Time")
        plt.legend()
        plt.show()

    def generate_puzzle_outcome_report(self):
        """
        Generate a single bar chart showing successes vs. failures by puzzle type overall.
        (Existing implementation kept for reusability.)
        """
        df = self.db_manager.get_puzzle_outcome_data()
        if df.empty:
            print("No game data available.")
            return

        x = df["type"]
        x_pos = range(len(x))
        width = 0.35

        plt.figure(figsize=(10, 6))
        plt.bar(x_pos, df["successes"], width=width, label="Successes")
        plt.bar([p + width for p in x_pos], df["failures"], width=width, label="Failures")
        plt.xticks([p + width / 2 for p in x_pos], x)
        plt.xlabel("Puzzle Type")
        plt.ylabel("Count")
        plt.title("Puzzle Outcomes by Type")
        plt.legend()
        plt.show()

    def generate_puzzle_outcomes_by_model_subplots(self):
        """
        Generate subplots of puzzle outcomes by type for each model.
        For each model, display a bar chart with successes and failures per puzzle type.
        """
        df = self.db_manager.get_puzzle_outcomes_by_model_data()
        if df.empty:
            print("No game data available.")
            return

        models = df["model_name"].unique()
        num_models = len(models)
        
        # Create subplots (arranged in one row or multiple rows if many models)
        cols = min(num_models, 3)  # up to 3 columns
        rows = (num_models + cols - 1) // cols
        fig, axes = plt.subplots(rows, cols, figsize=(cols * 4, rows * 4), squeeze=False)
        axes = axes.flatten()
        
        for idx, model in enumerate(models):
            ax = axes[idx]
            data = df[df["model_name"] == model]
            
            types = data["type"].tolist()
            successes = data["successes"].tolist()
            failures = data["failures"].tolist()
            x = range(len(types))
            width = 0.35
            
            ax.bar(x, successes, width=width, label='Successes')
            ax.bar([p + width for p in x], failures, width=width, label='Failures')
            ax.set_xticks([p + width / 2 for p in x])
            ax.set_xticklabels(types, rotation=45)
            
            ax.set_xlabel("Puzzle Type")
            ax.set_ylabel("Count")
            ax.set_title(model)
            ax.legend()
        
        # Hide any unused subplots
        for jdx in range(idx + 1, len(axes)):
            fig.delaxes(axes[jdx])
            
        plt.tight_layout()
        plt.show()

    def generate_illegal_moves_distribution(self):
        """
        Generate a pie chart showing the distribution of illegal moves by model.
        """
        df = self.db_manager.get_illegal_moves_data()
        if df.empty:
            print("No illegal moves data available.")
            return

        plt.figure(figsize=(8, 8))
        plt.pie(
            df["illegal_moves_count"],
            labels=df["model_name"],
            autopct="%1.1f%%",
            startangle=140
        )
        plt.title("Illegal Moves Distribution by Model")
        plt.show()

    def generate_final_ratings_intervals(self):
        """
        Generate a plot showing each model's final rating with a 95% confidence
        interval calculated as rating ± (2 × rating_deviation) and the weighted puzzle rating spread.
        Splits the "Model Final Rating" entry into separate entries for the marker and the error bar.
        """
        from matplotlib.lines import Line2D  # import proxy handle class

        df = self.db_manager.get_final_ratings_data()
        if df.empty:
            print("No ratings data available.")
            return

        # Calculate error as 2 × RD
        df['error'] = df['model_deviation'] * 2

        plt.figure(figsize=(8, 6))
        # Remove label from errorbar call
        plt.errorbar(
            df['model_name'], 
            df['model_rating'], 
            yerr=df['error'], 
            fmt='o', 
            ecolor='red', 
            capsize=5, 
            markersize=8
        )
        
        # Plot weighted puzzle rating spread if available
        weighted_rating, weighted_rd = self.db_manager.get_weighted_puzzle_rating()
        if weighted_rating is not None:
            puzzle_error = weighted_rd * 2
            plt.axhline(weighted_rating, color='green', linestyle='--')
            x_min, x_max = plt.xlim()
            plt.fill_between([x_min, x_max], weighted_rating - puzzle_error, weighted_rating + puzzle_error, 
                             color='green', alpha=0.2)

        # Create custom proxy handles for legend entries.
        # Proxies for model's final rating (blue dot) and its error bar (red line)
        marker_proxy = Line2D([], [], marker='o', color='blue', linestyle='None', markersize=8, label='Model Final Rating')
        spread_proxy = Line2D([], [], color='red', linestyle='-', linewidth=1, label='Model Rating Spread')
        
        handles = [marker_proxy, spread_proxy]
        
        # If weighted puzzle rating exists, create proxies for them as well.
        if weighted_rating is not None:
            weighted_proxy = Line2D([], [], color='green', linestyle='--', label='Weighted Puzzle Rating')
            # For the filled spread, using a thicker line to mimic the filled band.
            weighted_spread_proxy = Line2D([], [], color='green', linestyle='-', linewidth=10, alpha=0.2, label='Puzzle Rating Spread')
            handles.extend([weighted_proxy, weighted_spread_proxy])
        
        plt.xlabel("Model Name")
        plt.ylabel("Model Rating")
        plt.title("Final Model Ratings with 95% Confidence Intervals")
        plt.xticks(rotation=45)
        plt.grid(True)
        plt.legend(handles=handles)
        plt.show()

    def generate_correct_moves_percentage_report(self):
        """
        Generate a bar chart showing the average percentage of correct moves by model.
        The percentage is calculated as:
            (number of moves in game.model_solution / number of moves in puzzles.moves) * 100.
        """
        df = self.db_manager.get_moves_data()
        if df.empty:
            print("No moves data available.")
            return

        results = []
        for idx, row in df.iterrows():
            expected = row["moves"]
            # Split moves into lists (ignoring extra whitespace)
            expected_moves = expected.strip().split() if isinstance(expected, str) and expected.strip() else []
            num_expected = len(expected_moves)
            if num_expected == 0:
                continue

            model_solution = row["model_moves"]
            model_moves = model_solution.strip().split() if isinstance(model_solution, str) and model_solution.strip() else []
            # Calculate percentage of moves provided
            correct_pct = (len(model_moves) / num_expected) * 100

            results.append({"model_name": row["model_name"], "correct_pct": correct_pct})

        if not results:
            print("No valid moves to evaluate.")
            return

        df_pct = pd.DataFrame(results)
        avg_pct = df_pct.groupby("model_name")["correct_pct"].mean().reset_index()

        plt.figure(figsize=(10, 6))
        plt.bar(avg_pct["model_name"], avg_pct["correct_pct"], color="skyblue")
        plt.xlabel("Model Name")
        plt.ylabel("Average % of Correct Moves")
        plt.title("Average Percentage of Correct Moves by Model")
        plt.xticks(rotation=45)
        plt.ylim(0, 100)
        plt.grid(axis="y")
        plt.show()
        
# ---------------------------
# Main
# ---------------------------
async def main():
        # Set up puzzle selection
    csv_path = os.getenv('PUZZLE_PATH', 'puzzles.csv')
    
    # Initialize OpenRouter
    open_router = OpenRouter()

    # Initialize LLM models (simulate five different models)
    # Free llms
    free_reasoning_models = [
        LLMModel("qwen/qwq-32b:free", True, 6, open_router),
        LLMModel("google/gemini-2.0-pro-exp-02-05:free", True, 8, open_router),
        LLMModel("deepseek/deepseek-r1:free", True, 6, open_router),
    ]
    free_non_reasoning_models = [
        LLMModel("nvidia/llama-3.1-nemotron-70b-instruct:free", False, 6, open_router),
        LLMModel("mistralai/mistral-small-3.1-24b-instruct:free", False, 8, open_router),
        LLMModel("open-r1/olympiccoder-32b:free", False, 6, open_router),
    ]

    cheap_test = [
        LLMModel("meta-llama/llama-3.2-1b-instruct", False, 100, open_router),
        LLMModel("liquid/lfm-7b", False, 100, open_router),
        LLMModel("meta-llama/llama-3.2-3b-instruct", False, 100, open_router)
    ]
    
    # Initialize puzzle selector
    puzzle_selector = PuzzleSelector(csv_path)
    # Distribute puzzles individually: each model gets puzzles it has not yet seen.
    evaluators = [Evaluator(llm, puzzle_selector.get_puzzles_for_model(llm)) for llm in cheap_test]
    
    # Evaluate concurrently for all evaluators
    await asyncio.gather(*[evaluator.evaluate_all(target_deviation=50) for evaluator in evaluators])

if __name__ == "__main__":
    asyncio.run(main())


