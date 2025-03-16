import os
import pandas as pd
import matplotlib.pyplot as plt
import chess
import sqlite3
import requests
import json
import re
import asyncio

# ---------------------------
# Module 2: OpenRouter
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
# Module 1: LLM Models (LLM #1..5)
# ---------------------------
class LLMModel:
    def __init__(self, model_name:str, open_router:OpenRouter=OpenRouter()):
        self.model_name = model_name

    def get_move(self, fen, legal_moves, color):
        config = {
            "model": self.model_name, 
            "messages": [
                {
                    "role": "system",	
                    "content": f"Here's a chess board FEN string: {fen}"
                },
                {
                    "role": "system",
                    "content": f"Here are the SAN legal moves for {color}: {', '.join(legal_moves)}"
                },
                {
                    "role": "system",
                    "content": f"What is the best move for {color}? Answer only with one move in SAN (e.g. e4e5)"
                }
            ],
            "temperature": 0.0
        }
        return self.open_router.send_request(config)


# ---------------------------
# Module 4: Module de sélection de puzzles
# ---------------------------
class PuzzleSelector:
    """TODO"""

# ---------------------------
# Module 5: Environnement de jeu (python_chess)
# ---------------------------
class ChessEnvironment:
    def __init__(self, fen):
        self.board = chess.Board(fen)

    def get_legal_moves(self):
        """
        Returns the list of legal moves in SAN notation.
        """
        return [self.board.san(move) for move in self.board.legal_moves]
    
    def get_turn_color(self):
        """
        Returns the color of the side to move ('white' or 'black').
        """
        return "white" if self.board.turn == chess.WHITE else "black"

    def is_move_legal(self, move_san):
        """
        Checks if a given move (in SAN) is legal in the current board state.
        """
        try:
            move = self.board.parse_san(move_san)
            return move in self.board.legal_moves
        except Exception as e:
            print(f"Error validating move '{move_san}': {e}")
            return False

    def apply_move(self, move_san):
        """
        Applies the move to the board.
        """
        try:
            move = self.board.parse_san(move_san)
            self.board.push(move)
            return True
        except Exception as e:
            print(f"Failed to apply move '{move_san}': {e}")
            return False

# ---------------------------
# Module 7: Base de données (SQLite)
# ---------------------------
class DatabaseManager:
    """TODO"""

# ---------------------------
# Module 8: Module d’évaluation (Glicko-2)
# ---------------------------
class Evaluator:
    def __init__(self, llm:LLMModel, puzzles_df:pd.DataFrame):
        self.llm = llm
        self.puzzles_df = puzzles_df
        self.db_manager = DatabaseManager()

    def update_llm_rating(self, result):
        """TODO: Implement Glicko-2 rating update."""
    
    async def evaluate(self, target_deviation=0, num_retries=5):
        """
        Evaluate the LLM on a set of puzzles asynchronously.
        """
        # Iterate over puzzles
        for puzzle in self.puzzles_df:
            # Get the puzzle details
            solution = puzzle.get("Moves").split(' ')
            fen = puzzle.get("FEN")
            puzzle_id = puzzle.get("PuzzleId")
            puzzle_rating = puzzle.get("Rating")
            puzzle_deviation = puzzle.get("RatingDeviation")

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
                legal_moves = chess_env.get_legal_moves()
                
                # Get the LLM's move
                move = await self.llm.get_move(fen, legal_moves, color)
                failed_moves = []
                
                # Retry loop for invalid moves
                while not chess_env.validate_move(move) and len(failed_moves) < num_retries:
                    print(f"Invalid move received from {self.llm.model_name}. Retrying...")
                    failed_moves.append(move)
                    move = self.llm.retry_move(failed_moves, fen, legal_moves, color)

                # Append the move to the solution
                llm_solution.append(move)

                # Save the failed attempts  
                if len(failed_moves) > 0:
                    self.db_manager.save_failed_attempts(puzzle_id, self.llm.model_name, fen, failed_moves)

                # Check if the move is correct
                failed_puzzle = move != chess_env.get_san(solution[i+1])
                if failed_puzzle:
                    break
                
            # Save the result of the puzzle
            self.db_manager.save_game_result(puzzle_id, self.llm.model_name, failed_puzzle, llm_solution)
            # Update the LLM's rating and deviation
            rating, deviation, volatility = self.update_llm_rating(puzzle_rating, puzzle_deviation, failed_puzzle)
            # Save the updated benchmarks
            self.db_manager.save_benchmarks(self.llm.model_name, rating, deviation, volatility)

            # Check if the deviation is below the target
            if deviation < target_deviation:
                break

# ---------------------------
# Module 9: Module de création de rapports
# ---------------------------
class ReportGenerator:
    """TODO"""

# ---------------------------
# Example Workflow (Main)
# ---------------------------
def main():
    # Set up puzzle selection
    csv_path = os.getenv('PUZZLE_PATH', 'puzzles.csv')
    puzzle_selector = PuzzleSelector(csv_path)
    puzzles_400 = puzzle_selector.get_puzzles(400)
    puzzles_20 = puzzle_selector.get_puzzles(20)

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
    evaluators = [Evaluator(llm, puzzles_400) for llm in [qwq_llm, gemini_llm, deepseek_llm]]

    # Run evaluations asynchronously
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*[evaluator.evaluate(50) for evaluator in evaluators]))

    # Generate a simple report
    report_generator = ReportGenerator()
    report_generator.generate_report()

if __name__ == "__main__":
    main()
