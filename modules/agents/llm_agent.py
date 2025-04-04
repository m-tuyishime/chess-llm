import re
import logging
import traceback
from aiolimiter import AsyncLimiter
from typing import List, Optional

from .agent import Agent
from ..router import Router


# ---------------------------
# Module: LLM Agent
# ---------------------------
class LLMAgent(Agent):
    def __init__(self, model_name:str, is_reasoning:bool, open_router:Router, rate_per_minute:int=None):
        super().__init__(model_name, is_random=False, is_reasoning=is_reasoning)
        self.config = {
            "model": model_name,
            "messages": [], 
            "temperature": 0.0 # Set to 0.0 for deterministic responses
        }

        self.logger = logging.getLogger(f'chess_benchmark.model.{model_name}')
        
        # If rate_per_minute is not specified or exceeds router's limit, use router's limit
        router_max_rpm = open_router.max_rpm
        if rate_per_minute is None or rate_per_minute > router_max_rpm:
            self.rate_per_minute = router_max_rpm
            self.logger.info(f"Setting model {model_name} rate limit to router's maximum: {router_max_rpm} rpm")
        else:
            self.rate_per_minute = rate_per_minute
            self.logger.info(f"Setting model {model_name} rate limit to {rate_per_minute} rpm")
            
        self.open_router = open_router
        self.logger.info(f"Initializing LLM model {model_name} (reasoning: {is_reasoning}, rpm: {self.rate_per_minute})")

        # Create a limiter that allows 'rate_per_minute' requests per 60s
        self.limiter = AsyncLimiter(self.rate_per_minute, time_period=60)
        

    def _parse_move(self, response:Optional[str]) -> Optional[str]:
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
                "role": "user",
                "content": f"""
                Here's a chess board FEN string: {fen}
                Here are the SAN legal moves for {color}: {', '.join(legal_moves_san)}
                What is the best move for {color}? Answer only with one move in SAN notation.
                """
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
                
            move = self._parse_move(response["content"])
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
                    "role": "user",
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