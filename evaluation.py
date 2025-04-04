import os
import asyncio

from modules import setup_logging, Router, LLMAgent, RandomAgent, PuzzleSelector, Evaluator

# ---------------------------
# Main
# ---------------------------
async def main():
    # Create the logger
    logger = setup_logging()

    open_router_url = "https://openrouter.ai/api/v1/chat/completions"
    open_router_key = os.getenv('OPENROUTER_API_KEY')

    nim_url = "https://integrate.api.nvidia.com/v1/chat/completions"
    nim_key = os.getenv('NIM_API_KEY')
    
    # Initialize Router
    open_router = Router(open_router_url, open_router_key)
    nim_router = Router(nim_url, nim_key, 40)

    # Initialize LLM models (simulate five different models)
    # Free llms from OpenRouter 20 rpm/200 rpd
    or_free_models = [
        LLMAgent("google/gemini-2.0-pro-exp-02-05:free", True, open_router, 1),
        LLMAgent("google/gemini-2.5-pro-exp-03-25:free", True, open_router, 1),
        LLMAgent("deepseek/deepseek-v3-base:free", False, open_router, 12),
    ]

    or_cheap_models = [
        LLMAgent("meta-llama/llama-3.1-8b-instruct", False, open_router)
    ]

    nim_models = [
        LLMAgent("deepseek-ai/deepseek-r1", True, nim_router),
        LLMAgent("qwen/qwq-32b", True, nim_router),
        LLMAgent("deepseek-ai/deepseek-r1-distill-llama-8b", False, nim_router),
        LLMAgent("meta/llama-3.1-405b-instruct", False, nim_router),
        LLMAgent("google/gemma-3-27b-it", False, nim_router),
    ]

    random_agent = [
        RandomAgent()
    ]
    
    # Initialize puzzle selector
    puzzle_selector = PuzzleSelector()
    # Distribute puzzles individually: each model gets puzzles it has not yet seen.
    evaluators = [Evaluator(llm, puzzle_selector.get_puzzles_for_model(llm)) for llm in nim_models + or_cheap_models + random_agent]
    
    # Evaluate concurrently for all evaluators
    await asyncio.gather(*[evaluator.evaluate_all(target_deviation=50) for evaluator in evaluators])

if __name__ == "__main__":
    asyncio.run(main())


