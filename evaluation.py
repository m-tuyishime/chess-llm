import os
import asyncio

from modules import setup_logging, Router, LLMAgent, RandomAgent, PuzzleSelector, Evaluator, StockfishAgent

# ---------------------------
# Main
# ---------------------------
async def main():
    # Create the logger
    setup_logging()

    open_router_url = "https://openrouter.ai/api/v1"
    open_router_key = os.getenv('OPENROUTER_API_KEY')

    nim_url = "https://integrate.api.nvidia.com/v1"
    nim_key = os.getenv('NIM_API_KEY')
    
    # Initialize Router
    open_router = Router(open_router_url, open_router_key)
    nim_router = Router(nim_url, nim_key, 40)



    nim_models = [
        LLMAgent(nim_router, "nvidia/llama-3.1-nemotron-ultra-253b-v1", True),
        LLMAgent(nim_router, "meta/llama-3.1-405b-instruct", False),
        LLMAgent(nim_router, "google/gemma-3-27b-it", False),
        LLMAgent(nim_router, "meta/llama-3.1-8b-instruct", False),
        LLMAgent(nim_router, "meta/llama-4-maverick-17b-128e-instruct", False),
        # LLMAgent(nim_router, "deepseek-ai/deepseek-r1", True),
    ]

    other_agents = [
        RandomAgent(), 
        StockfishAgent(level=1),
    ]
    
    # Initialize puzzle selector
    puzzle_selector = PuzzleSelector()
    # Distribute puzzles individually: each model gets puzzles it has not yet seen.
    evaluators = [Evaluator(llm, puzzle_selector.get_puzzles_for_model(llm)) for llm in nim_models + other_agents]
    
    # Evaluate concurrently for all evaluators
    await asyncio.gather(*[evaluator.evaluate_all() for evaluator in evaluators])

if __name__ == "__main__":
    asyncio.run(main())


