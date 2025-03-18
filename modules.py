from functools import reduce
import os
import pandas as pd
import matplotlib.pyplot as plt
import chess
import sqlite3
import requests
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

    def send_request(self, body):
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
            },
            data=json.dumps(body)
        )
        return response.json()['choices'][0]['message']['content']

# ---------------------------
# Module: LLM Models 
# ---------------------------
class LLMModel:
    def __init__(self, model_name:str, open_router:OpenRouter=OpenRouter()):
        self.model_name = model_name
        self.config = {
            "model": model_name,
            "messages": [], 
            "temperature": 0.0 # Set to 0.0 for deterministic responses
        }
        self.open_router = open_router
        self.player = glicko2.Player()

    def get_move(self, fen, legal_moves_san, color):
        """
        Get the best move for a given board state.
        """
        # Set the messages for the model
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
        return self.open_router.send_request(self.config)
    
    def retry_move(self, failed_moves_san, fen, legal_moves_san, color):
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
        
        return self.open_router.send_request(self.config)
        



# ---------------------------
# Module: Sélection de puzzles
# ---------------------------
class PuzzleSelector:
    def __init__(self, csv_path):
        self.puzzles_df = pd.read_csv(csv_path)

    def get_tactic_puzzles(self, tactic:int=0) -> pd.DataFrame:
        """
        TODO Get tactic puzzles
        """
    
    def get_strategy_puzzles(self, strategy:int=0) -> pd.DataFrame:
        """
        TODO Get strategy puzzles
        """

    def get_endgame_puzzles(self, endgame:int=0) -> pd.DataFrame:
        """
        TODO Get endgame puzzles
        """

    def get_mate_puzzles(self, mate:int=0) -> pd.DataFrame:
        """
        TODO Get mate puzzles
        """
    
    def get_puzzles(self, mate:int=0, tactic:int=0, strategy:int=0, endgame:int=0) -> pd.DataFrame:
        """
        Get a selection of puzzles based on the specified categories.
        """
        return reduce(lambda left, right: pd.merge(left, right, on="PuzzleId"), [
            self.get_mate_puzzles(mate),
            self.get_tactic_puzzles(tactic),
            self.get_strategy_puzzles(strategy),
            self.get_endgame_puzzles(endgame)
        ])

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

    def is_move_legal(self, move_san) -> bool:
        """
        Checks if a given move (in SAN) is legal in the current board state.
        """
        return move_san in self.get_legal_moves()

    def apply_move(self, move_san) -> str:
        """
        Applies the move to the board and returns the new FEN string.
        """
        self.board.push_san(move_san)
        return self.board.fen()
    def uci_to_san(self, uci):
        """
        Convert UCI move to SAN move.
        """
        return self.board.san(chess.Move.from_uci(uci))


# ---------------------------
# Module: Base de données (SQLite)
# ---------------------------
class DatabaseManager:
    def __init__(self, db_path=os.getenv("DB_PATH")):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

    def save_game_result(self, puzzle_id:int, model_name:str, failed_puzzle:bool, solution:list):
        """
        Save the result of a puzzle game to the database.
        """
        self.cursor.execute(
            "INSERT INTO game_results (puzzle_id, model_name, failed_puzzle, solution) VALUES (?, ?, ?, ?)",
            (puzzle_id, model_name, failed_puzzle, json.dumps(solution))
        )
        self.conn.commit()

    def save_failed_attempts(self, puzzle_id:int, model_name:str, fen:str, failed_moves:list):
        """
        Save the failed attempts of a puzzle to the database.
        """
        self.cursor.execute(
            "INSERT INTO failed_attempts (puzzle_id, model_name, fen, failed_moves) VALUES (?, ?, ?, ?)",
            (puzzle_id, model_name, fen, json.dumps(failed_moves))
        )
        self.conn.commit()

    def save_benchmarks(self, puzzle_id:int, model_name:str, rating:int, deviation:int, volatility:int):
        """
        Save the updated benchmarks of a model to the database.
        """
        self.cursor.execute(
            "INSERT INTO benchmarks (puzzle_id, model_name, rating, deviation, volatility) VALUES (?, ?, ?, ?, ?)",
            (puzzle_id, model_name, rating, deviation, volatility)
        )
        self.conn.commit()

# ---------------------------
# Module: Module d’évaluation 
# ---------------------------
class Evaluator:
    def __init__(self, llm:LLMModel, puzzles_df:pd.DataFrame):
        self.llm = llm
        self.puzzles_df = puzzles_df
        self.db_manager = DatabaseManager()

    def update_llm_rating(self, puzzle_rating:int, puzzle_deviation:int, failed_puzzle:bool):
        """
        Update the LLM's rating and deviation based on the result of a puzzle.
        """
        # Update the player's rating
        self.llm.player.update_player(puzzle_rating, puzzle_deviation, failed_puzzle)
        return self.llm.player.rating, self.llm.player.rd, self.llm.player.vol

    
    async def evaluate(self, target_deviation=0, num_retries=5):
        """
        Evaluate the LLM on a set of puzzles asynchronously.
        """
        # Iterate over puzzles
        for puzzle in self.puzzles_df.iterrows():
            # Get the puzzle details
            solution = puzzle["Moves"].split(' ')
            fen = puzzle["FEN"]
            puzzle_id = puzzle["PuzzleId"]
            puzzle_rating = puzzle["Rating"]
            puzzle_deviation = puzzle["RatingDeviation"]

            chess_env = ChessEnvironment(fen)
            failed_puzzle = False
            llm_solution = []
            # Iterate over the moves needed to solve the puzzle, in pairs
            for i in range(len(solution), step=2):
                # Play the opponent's move
                fen = chess_env.apply_move(solution[i])
                llm_solution.append(solution[i])

                # Get the initial legal moves and color
                color = chess_env.get_turn_color()
                legal_moves_san = chess_env.get_legal_moves()
                
                # Get the LLM's move
                move = await self.llm.get_move(fen, legal_moves_san, color)
                failed_moves_san = []
                
                # Retry loop for invalid moves
                while not chess_env.is_move_legal(move) and len(failed_moves_san) < num_retries:
                    print(f"Invalid move received from {self.llm.model_name}. Retrying...")
                    failed_moves_san.append(move)
                    move = self.llm.retry_move(failed_moves_san, fen, legal_moves_san, color)

                # Append the move to the solution
                llm_solution.append(move)

                # Save the failed attempts  
                if len(failed_moves_san) > 0:
                    self.db_manager.save_failed_attempts(puzzle_id, self.llm.model_name, fen, failed_moves_san)

                # Check if the move is correct
                failed_puzzle = move != chess_env.uci_to_san(solution[i+1])
                if failed_puzzle:
                    break
                
            # Save the result of the puzzle
            self.db_manager.save_game_result(puzzle_id, self.llm.model_name, failed_puzzle, llm_solution)
            # Update the LLM's rating and deviation
            rating, deviation, volatility = self.update_llm_rating(puzzle_rating, puzzle_deviation, failed_puzzle)
            # Save the updated benchmarks
            self.db_manager.save_benchmarks(puzzle_id, self.llm.model_name, rating, deviation, volatility)

            # Check if the deviation is below the target
            if deviation < target_deviation:
                break

# ---------------------------
# Module: Création de rapports
# ---------------------------
class ReportGenerator:
    """TODO"""

# ---------------------------
# Main
# ---------------------------
def main():
    # Set up puzzle selection
    csv_path = os.getenv('PUZZLE_PATH', 'puzzles.csv')
    puzzle_selector = PuzzleSelector(csv_path)
    puzzles_800 = puzzle_selector.get_puzzles(mate=200, tactic=200, strategy=200, endgame=200)
    puzzles_20 = puzzle_selector.get_puzzles(mate=5, tactic=5, strategy=5, endgame=5)

    # Initialize OpenRouter
    open_router = OpenRouter()

    # Initialize LLM models (simulate five different models)
    # Free llms
    qwq_llm = LLMModel("qwen/qwq-32b:free", open_router)
    gemini_llm = LLMModel("google/gemini-2.0-pro-exp-02-05:free", open_router)
    deepseek_llm = LLMModel("deepseek/deepseek-r1-zero:free", open_router)

    # Paid llms
    o3_llm = LLMModel("openai/o3-mini-high", open_router)
    claude_llm = LLMModel("anthropic/claude-3.7-sonnet:thinking", open_router)

    # Initialize evaluators for each LLM
    evaluators = [Evaluator(llm, puzzles_800) for llm in [qwq_llm, gemini_llm, deepseek_llm]]

    # Run evaluations asynchronously
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*[evaluator.evaluate(50) for evaluator in evaluators]))

if __name__ == "__main__":
    main()
