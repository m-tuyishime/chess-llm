from functools import reduce
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

    async def send_request(self, body):
        """
        Send a request to the OpenRouter API.
        """
        timeout = aiohttp.ClientTimeout(total=60)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self.base_url, headers=self.headers, json=body) as response:
                    response_data = await response.json()
        except (asyncio.TimeoutError) as e:
            print(f"Request timed out: {e}")
            return None
        if "choices" not in response_data:
            print(f"Error: {response_data}")
            return None  # Exit this request/task on error
        return response_data["choices"][0]["message"]["content"]

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
        else:
            # If no benchmark exists, create a new player with default values
            self.player = glicko2.Player()

        # Create a limiter that allows 'rate_per_minute' requests per 60s
        self.limiter = AsyncLimiter(rate_per_minute, time_period=60)
        

    def parse_move(self, response:Optional[str]) -> Optional[str]:
        """
        Parse the move from the model's response. Returns None if no move is found.
        """
        if not response or not isinstance(response, str):
            return None
        match = re.search(r'(?:move:\s*)?([KQRBN]?(?:[a-h][1-8]|[a-h]?x[a-h][1-8])[+#]?)', response)
        if match:
            return match.group(1)
        else:
            return None

    async def get_move(self, fen:str, legal_moves_san:List[str], color:str) -> Optional[str]:
        """
        Get the best move for a given board state.
        """
        self.config["messages"] = [
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
            },
            {
                "role": "assistant",
                "content": "move: "
            }
        ]

        async with self.limiter:
            response = await self.open_router.send_request(self.config)
        return self.parse_move(response)
    
    async def retry_move(self, failed_moves_san:List[str], fen:str, legal_moves_san:List[str], color:str) -> Optional[str]:
        """
        Reprompt the model for a move after a failed attempt.
        """
        base_messages = [
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
            },
        ]
        
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
        
        # Final prompt message
        final_prompt = [
            {
                "role": "assistant",
                "content": "move: "
            }
        ]
        
        # Combine all messages together
        self.config["messages"] = base_messages + retry_messages + final_prompt
        
        async with self.limiter:
            response = await self.open_router.send_request(self.config)
        return self.parse_move(response)
        

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
    
    def get_puzzles(self, models: List[LLMModel]) -> pd.DataFrame:
        """
        Get a selection of puzzles based on the specified categories.
        Alternates one mate, one tactic, one strategy and one endgame puzzle until one category runs out.
        If no puzzles exist in the database, new puzzles are created and inserted.
        If puzzles exist but no uncompleted ones remain, print a message and exit.
        Otherwise, returns the uncompleted puzzles.
        """
        all_puzzles = self.db_manager.get_puzzles()
        uncompleted = self.db_manager.get_uncompleted_puzzles(models)
        
        # If puzzles exist but there are no uncompleted puzzles, exit.
        if all_puzzles is not None and uncompleted is None:
            print("All puzzles have already been evaluated. Exiting.")
            exit(0)
        # No puzzles saved at all? Build new puzzles selection.
        elif all_puzzles is None:
            mate_df = self.get_mate_puzzles()
            tactic_df = self.get_tactic_puzzles()
            strategy_df = self.get_strategy_puzzles()
            endgame_df = self.get_endgame_puzzles()
            
            # Ensure each category has at least one puzzle.
            if any(len(df) == 0 for df in [mate_df, tactic_df, strategy_df, endgame_df]):
                raise ValueError("One or more puzzle categories are empty.")
            
            # Determine number of full cycles (one from each category)
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
            # Insert the new puzzles into the database
            return self.db_manager.insert_puzzles(combined_df)
        else:
            # Otherwise, return the uncompleted puzzles.
            return uncompleted


# ---------------------------
# Module: Environnement de jeu 
# ---------------------------
class ChessEnvironment:
    def __init__(self, fen):
        self.board = chess.Board(fen)

    def get_legal_moves(self) -> list:
        """
        Returns the list of legal moves in SAN notation.
        """
        return [self.board.san(move) for move in self.board.legal_moves]
    
    def get_turn_color(self) -> str:
        """
        Returns the color of the side to move ('white' or 'black').
        """
        return "white" if self.board.turn == chess.WHITE else "black"

    def is_move_legal(self, move_san: str) -> bool:
        """
        Checks if a given move (in SAN) is legal in the current board state.
        """
        return move_san in self.get_legal_moves()

    def apply_move(self, move_san: str) -> str:
        """
        Applies the move to the board and returns the new FEN string.
        """
        self.board.push_san(move_san)
        return self.board.fen()
    def uci_to_san(self, uci: str) -> str:
        """
        Convert UCI move to SAN move.
        """
        return self.board.san(chess.Move.from_uci(uci))


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
        
        self.db_path = os.getenv("DB_PATH", "data/storage.db")
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self._initialized = True

    def create_tables(self):
        """
        Create the necessary tables in the database.
        """
        # Enable foreign key constraints
        self.cursor.execute("PRAGMA foreign_keys = ON;")
        
        # Create puzzles table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS puzzles (
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
        
        # Create models table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS models (
                name TEXT PRIMARY KEY,
                reasoning BOOLEAN
            )
        ''')
        
        # Create game table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS game (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                puzzle_id TEXT REFERENCES puzzles(id) ON DELETE CASCADE,
                model_name TEXT REFERENCES models(name) ON DELETE CASCADE,
                date TEXT DEFAULT (date('now')),
                failed_puzzle BOOLEAN,
                model_solution TEXT
            )
        ''')
        
        # Create illegal_moves table 
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS illegal_moves (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER REFERENCES game(id) ON DELETE CASCADE,
                fen TEXT,
                correct_move TEXT,
                failed_move TEXT
            )
        ''')
        
        # Create benchmarks table 
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS benchmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER REFERENCES game(id) ON DELETE CASCADE,
                model_rating INTEGER,
                model_deviation INTEGER,
                model_volatility INTEGER
            )
        ''')
        
        self.conn.commit()

    def insert_puzzles(self, puzzles_df: pd.DataFrame) -> pd.DataFrame:
        """
        Insert the selected puzzles into the database.
        """
        # Convert DataFrame to list of tuples
        puzzles = puzzles_df.to_records(index=False).tolist()
        
        # Insert puzzles into the database
        self.cursor.executemany('''
            INSERT OR IGNORE INTO puzzles (id, fen, moves, rating, rating_deviation, popularity, nb_plays, themes, game_url, opening_tags, type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', puzzles)
        
        self.conn.commit()
        return self.get_puzzles()

    def create_model(self, model_name: str, reasoning: bool):
        """
        Create a new model entry in the database.
        """
        self.cursor.execute(
            "INSERT OR IGNORE INTO models (name, reasoning) VALUES (?, ?)",
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

    def save_game_result(self, game_id: int, failed_puzzle: bool, model_solution: list):
        """
        Save the result of a game to the database.
        """
        self.cursor.execute(
            "UPDATE game SET failed_puzzle = ?, model_solution = ? WHERE id = ?",
            (failed_puzzle, json.dumps(model_solution), game_id)
        )
        self.conn.commit()

    def save_illegal_moves(self, game_id: int, fen: str, correct_move: str, failed_move: str):
        """
        Save the illegal moves made by the model during a game.
        """
        self.cursor.execute(
            "INSERT INTO illegal_moves (game_id, fen, correct_move, failed_move) VALUES (?, ?, ?, ?)",
            (game_id, fen, correct_move, failed_move)
        )
        self.conn.commit()

    def save_benchmarks(self, game_id: int, model_rating: int, model_deviation: int, model_volatility: int):
        """
        Save the benchmarks for a game.
        """
        self.cursor.execute(
            "INSERT INTO benchmarks (game_id, model_rating, model_deviation, model_volatility) VALUES (?, ?, ?, ?)",
            (game_id, model_rating, model_deviation, model_volatility)
        )
        self.conn.commit()
    
    def get_puzzles(self) -> Optional[pd.DataFrame]:
        """
        Get all puzzles from the database.
        """
        self.cursor.execute("SELECT * FROM puzzles")
        rows = self.cursor.fetchall()
        
        if not rows:
            return None
        
        columns = [column[0] for column in self.cursor.description]
        return pd.DataFrame(rows, columns=columns)

    def get_uncompleted_puzzles(self, models: List[LLMModel]) -> Optional[pd.DataFrame]:
        """
        Get uncompleted puzzles from the database.
        """
        # Get the IDs of the models
        model_names = [model.model_name for model in models]
        placeholders = ', '.join('?' * len(model_names))
        
        query = f'''
            SELECT p.*
            FROM puzzles p
            LEFT JOIN game g ON p.id = g.puzzle_id AND g.model_name IN ({placeholders})
            WHERE g.id IS NULL OR g.failed_puzzle IS NULL
        '''
        
        self.cursor.execute(query, model_names)
        rows = self.cursor.fetchall()

        # Get the column names
        columns = [column[0] for column in self.cursor.description]
        
        # Delete uncompleted games for the specified models to avoid complications
        delete_query = f"DELETE FROM game WHERE model_name IN ({placeholders}) AND failed_puzzle IS NULL"
        self.cursor.execute(delete_query, model_names)
        self.conn.commit()
        
        if not rows:
            return None
        return pd.DataFrame(rows, columns=columns)
    
    def get_last_benchmarks(self, model_name: str) -> Optional[tuple]:
        """
        Get the most recent benchmarks for a given model from the database.
        """
        query = '''
            SELECT b.model_rating, b.model_deviation, b.model_volatility
            FROM benchmarks b
            JOIN game g ON b.game_id = g.id
            WHERE g.model_name = ?
            ORDER BY b.id DESC LIMIT 1
        '''
        self.cursor.execute(query, (model_name,))
        row = self.cursor.fetchone()
        return row if row else None

# ---------------------------
# Module: Module d’évaluation 
# ---------------------------
class Evaluator:
    def __init__(self, llm:LLMModel, puzzles_df:pd.DataFrame):
        self.llm = llm
        self.puzzles_df = puzzles_df
        self.db_manager = DatabaseManager()

    def update_llm_rating(self, puzzle_ratings:List[int], puzzle_deviations:List[int], puzzle_wins:List[bool]):
        """
        Update the LLM's rating and deviation based on the results of the puzzles.
        """
        self.llm.player.update_player(puzzle_ratings, puzzle_deviations, puzzle_wins)
        return self.llm.player.rating, self.llm.player.rd, self.llm.player.vol
    
    async def evaluate_puzzle(self, puzzle:pd.Series) -> Optional[tuple]:
        """
        Evaluate a single puzzle. On error, exit early; do not complete the puzzle.
        Returns (rating, deviation, volatility) if evaluated.
        """
        db = self.db_manager
        puzzle_id = puzzle.id
        fen = puzzle.fen
        solution = puzzle.moves.split(" ")
        puzzle_rating = puzzle.rating
        puzzle_deviation = puzzle.rating_deviation


        game_id = db.create_game(puzzle_id, self.llm.model_name)
        chess_env = ChessEnvironment(fen)
        llm_solution = []
        failed_puzzle = False

        # Iterate through the moves of the solution in pairs (opponent's move, model's move)
        for i in range(0, len(solution), 2):
            # Play the opponent's move
            opponent_move = chess_env.uci_to_san(solution[i])
            # Get the new FEN after applying the opponent's move
            fen = chess_env.apply_move(opponent_move)
            # Append the opponent's move to the LLM solution
            llm_solution.append(opponent_move)

            # Get the color of the side to move
            color = chess_env.get_turn_color()
            # Get the legal moves for the current position
            legal_moves_san = chess_env.get_legal_moves()
            # Get the expected move from the solution
            expected_move = chess_env.uci_to_san(solution[i+1])
            # LLM generates a move
            move = await self.llm.get_move(fen, legal_moves_san, color)

            if move is None:
                # Exit this task early request error, leaving puzzle uncompleted
                return None
            
            # Store the illegal moves
            illegal_moves_san = []
            # Retry until a legal move is found or 5 illegal moves are stored
            while not chess_env.is_move_legal(move) and len(illegal_moves_san) < 5:
                illegal_moves_san.append(move)
                move = await self.llm.retry_move(illegal_moves_san, fen, legal_moves_san, color)
                if move is None:
                    # Exit this task early request error, leaving puzzle uncompleted
                    return None
            # If the move is still illegal after retries, mark the puzzle as failed
            if not chess_env.is_move_legal(move):
                failed_puzzle = True
                break

            # Apply the move to the board and get the new FEN
            fen = chess_env.apply_move(move)
            llm_solution.append(move)

            # Save the illegal moves to the database
            if illegal_moves_san:
                db.save_illegal_moves(game_id, fen, expected_move, move)
            
            # Check if the move matches the expected move
            if move != expected_move:
                failed_puzzle = True
                break
        

        db.save_game_result(game_id, failed_puzzle, llm_solution)
        rating, deviation, volatility = self.update_llm_rating([puzzle_rating], [puzzle_deviation], [not failed_puzzle])
        db.save_benchmarks(game_id, rating, deviation, volatility)
        return (rating, deviation, volatility)

    async def evaluate_all(self, target_deviation: int) -> None:
        # Create tasks for all puzzles to run concurrently
        tasks = [asyncio.create_task(self.evaluate_puzzle(puzzle)) for puzzle in self.puzzles_df.itertuples()]
        for task in asyncio.as_completed(tasks):
            try:
                result = await task
            except asyncio.CancelledError:
                continue
            if result is None:
                continue
            _, deviation, _ = result
            if deviation < target_deviation:
                # Cancel any remaining tasks if target condition is met
                for pending in tasks:
                    if not pending.done():
                        pending.cancel()
                break

# ---------------------------
# Module: Création de rapports
# ---------------------------
class ReportGenerator:
    """TODO"""

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

    # Paid llms
    # o3 = LLMModel("openai/o3-mini-high", open_router)
    # claude = LLMModel("anthropic/claude-3.7-sonnet:thinking", open_router)

    # Initialize puzzle selector
    puzzle_selector = PuzzleSelector(csv_path)
    puzzles = puzzle_selector.get_puzzles(free_non_reasoning_models)

    # Distribute puzzles round-robin among evaluators
    evaluators = [Evaluator(llm, puzzles) for llm in free_non_reasoning_models]
    
    # Evaluate concurrently for all evaluators
    await asyncio.gather(*[evaluator.evaluate_all(target_deviation=50) for evaluator in evaluators])

if __name__ == "__main__":
    asyncio.run(main())
