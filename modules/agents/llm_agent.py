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
    def __init__(self, router:Router, model_name:str, is_reasoning:bool, rate_per_minute:int=None) -> None:
        """
        Initialize the LLM agent with a specific model and router.
        :param router: The router instance for API requests.
        :param model_name: The name of the model to use.
        :param is_reasoning: Whether the model is for reasoning tasks.
        :param rate_per_minute: The rate limit for the model in requests per minute.
        """
        
        super().__init__(model_name, is_random=False, is_reasoning=is_reasoning)
        self.config = {
            "model": model_name,
            "messages": [], 
            "temperature": 0.6, # To avoid repetitive responses
            "top_p": 0.95, # To avoid repetitive responses
        }

        self.logger = logging.getLogger(f'chess_benchmark.model.{model_name}')
        
        # If rate_per_minute is not specified or exceeds router's limit, use router's limit
        router_max_rpm = router.max_rpm
        if rate_per_minute is None or rate_per_minute > router_max_rpm:
            self.rate_per_minute = router_max_rpm
            self.logger.info(f"Setting model {model_name} rate limit to router's maximum: {router_max_rpm} rpm")
        else:
            self.rate_per_minute = rate_per_minute
            self.logger.info(f"Setting model {model_name} rate limit to {rate_per_minute} rpm")
            
        self.router = router
        self.logger.info(f"Initializing LLM model {model_name} (reasoning: {is_reasoning}, rpm: {self.rate_per_minute})")

        # Create a limiter that allows 'rate_per_minute' requests per 60s
        self.limiter = AsyncLimiter(self.rate_per_minute, time_period=60)
        

    def _parse_move(self, response:Optional[str]) -> Optional[str]:
        """
        Parse the move from the model's response. Returns None if no move is found.
        """
        if not response:
            self.logger.warning(f"Received empty response from model {self.model_name}")
            return None
            
        match = re.search(r'<FinalMove>\s*(.*?)\s*</FinalMove>', response)
        if match:
            move = match.group(1)
            self.logger.debug(f"Parsed move: {move}")
            return move
        else:
            self.logger.warning(f"Failed to parse move from response: {response[-300:]}...")
            return None

    def _create_base_messages(self, fen: str, legal_moves_san: List[str], color: str) -> List[dict]:
        """
        Create the base messages for a chess move prompt.
        """
        return [
            {
                "role": "user",
                "content": f"""
                    You are a world-class chess grandmaster and expert analyst. You are presented with the following chess puzzle:

                    Chess board position (FEN): {fen}
                    Legal moves for {color}: {', '.join(legal_moves_san)}

                    Analyze the position. Then, on a new line, output your final chosen move in Standard Algebraic Notation (SAN) enclosed in <FinalMove> tags. For example:

                    <FinalMove>b5</FinalMove>

                    Ensure that the final output line contains only the <FinalMove> tag with the move and no additional text, markdown, or formatting.
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
                response = await self.router.send_request(self.config)
                
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
        messages = self._create_base_messages(fen, legal_moves_san, color)

        # Add the messages to the config
        self.config["messages"] = messages
        
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
                    "content": f"<FinalMove>{move}</FinalMove>"
                },
                {
                    "role": "user",
                    "content": "Invalid move. Please try again."
                }
            ])
        
        
        # Combine all messages together
        self.config["messages"] = base_messages + retry_messages
        
        # Make the API request with a prefix for logs
        return await self._make_api_request("Retry: ")