import asyncio
import json
import logging
import random
import traceback
from datetime import datetime
from typing import Optional
from aiolimiter import AsyncLimiter
from openai import AsyncOpenAI

# ---------------------------
# Module: Router
# ---------------------------
class Router:
    def __init__(self, base_url:str, api_key:str, max_rpm:int=100) -> None:
        """
        Initialize the Router with the base URL and API key.
        :param base_url: The base URL for the Router API.
        :param api_key: The API key for authentication.
        :param max_rpm: The maximum requests per minute allowed for the Router.
        """
        self.api_key = api_key
        self.base_url = base_url
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
        )

        self.logger = logging.getLogger('chess_benchmark.router')
        
        self.max_rpm = max_rpm
        # Create a rate limiter that allows 'max_rpm' requests per 60s
        self._super_limiter = AsyncLimiter(max_rpm, time_period=60)

        self.logger.info(f"Initialized super rate limiter with {max_rpm} requests per minute")
    

    async def send_request(self, body:dict) -> Optional[dict]:
        """
        Send a request to the Router API with rate limiting.
        """
        model = body["model"]
        self.logger.debug(f"Sending request to Router for model {model}")
        full_response_content = ""
        start_time = None
        
        try:
            start_time = datetime.now()
            # Apply super rate limiter before making the request
            self.logger.debug(f"Waiting for super rate limiter ({self.max_rpm} rpm)")
            async with self._super_limiter:
                await asyncio.sleep(random.uniform(0, 59))  
                completion = await self.client.chat.completions.create(
                    model=model,
                    messages=body["messages"],
                    temperature=body["temperature"],
                    top_p=body["top_p"],
                    stream=False,
                )

                self.logger.debug(f"Request payload: {json.dumps(body)[:500]}...")
            
            elapsed = (datetime.now() - start_time).total_seconds()
            self.logger.debug(f"Received response in {elapsed:.2f}s")

        except Exception as e:
            self.logger.error(f"Error during API request for model {model}: {e}")
            self.logger.error(traceback.format_exc())
            return None
            
        if not completion or not hasattr(completion, 'choices') or not completion.choices:
            self.logger.error(f"Error in API response for model {model}: {completion}")
            return None

        content = completion.choices[0].message.content
        pt = completion.usage.prompt_tokens
        ct = completion.usage.completion_tokens
        
        self.logger.debug(f"API response for {model}: {content[:100]}... (pt: {pt}, ct: {ct})")
        return {
            "content": content,
            "prompt_tokens": pt,
            "completion_tokens": ct
        }