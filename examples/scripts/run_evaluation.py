import asyncio
import logging
import os

from chess_llm_eval.agents.llm import LLMAgent
from chess_llm_eval.agents.random import RandomAgent
from chess_llm_eval.agents.stockfish import StockfishAgent
from chess_llm_eval.core.evaluator import Evaluator
from chess_llm_eval.data.sqlite import SQLiteRepository
from chess_llm_eval.providers.openrouter import OpenRouterProvider
from chess_llm_eval.utils.logging import setup_logging


async def main() -> None:
    """
    Main entry point for the Chess LLM Evaluation Benchmark.
    """
    setup_logging()

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is not set")

    base_url = "https://openrouter.ai/api/v1"

    # Initialize OpenRouter Provider
    provider = OpenRouterProvider(base_url, api_key, max_rpm=50)

    # Initialize Repository
    repo = SQLiteRepository("data/storage.db")  # Using default path or relative

    # Define agents
    # Note: Evaluator expects 'Agent' instances.
    models = [
        LLMAgent(provider, "nvidia/llama-3.1-nemotron-70b-instruct", is_reasoning=True),
        LLMAgent(provider, "meta-llama/llama-3.1-405b-instruct", is_reasoning=False),
        LLMAgent(provider, "google/gemma-2-27b-it", is_reasoning=False),
        LLMAgent(provider, "meta-llama/llama-3.1-8b-instruct", is_reasoning=False),
    ]

    other_agents = [
        RandomAgent(),
        StockfishAgent(level=1),
    ]

    all_agents = models + other_agents

    # In the new design, Evaluator orchestrates the eval for a list of agents or one by one.
    # The original script created one Evaluator per agent.
    # Let's adapt to the new Evaluator signature if needed.
    # Looking at core/evaluator.py, it takes (agent, puzzles, repository).

    # Fetch puzzles from repository or selector?
    # The new library might handle puzzle fetching via repo.
    # Let's use the repository to get uncompleted puzzles for each agent.

    evaluators = []
    for agent in all_agents:
        # Check if agent exists in DB, if not save it? Evaluator might handle it or we do it here.
        # Ideally, we ensure agent exists.
        # repo.save_agent(AgentData(...)) - simpler if Evaluator or Agent handles registration,
        # but let's assume Evaluator logic handles the game loop.

        # We need to fetch puzzles.
        # For this example, let's fetch a small batch of puzzles from DB.
        # If DB is empty, we might need a seeder. Assuming DB has puzzles.
        puzzles = repo.get_uncompleted_puzzles(agent.model_name, limit=10)

        if not puzzles:
            logging.info(f"No puzzles found for {agent.model_name}")
            continue

        evaluator = Evaluator(agent, puzzles, repo)
        evaluators.append(evaluator)

    if evaluators:
        await asyncio.gather(*[evaluator.evaluate_all() for evaluator in evaluators])
    else:
        logging.info("No evaluations to run.")


if __name__ == "__main__":
    asyncio.run(main())
