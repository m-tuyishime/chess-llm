import aiohttp
import asyncio
import json
import logging
import traceback
from datetime import datetime
from aiolimiter import AsyncLimiter

# ---------------------------
# Module: Router
# ---------------------------
class Router:
    def __init__(self, base_url:str, api_key:str, max_rpm:int=100):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.logger = logging.getLogger('chess_benchmark.openrouter')
        
        self.max_rpm = max_rpm
        # Create a rate limiter that allows 'max_rpm' requests per 60s
        self._super_limiter = AsyncLimiter(max_rpm, time_period=60)

        self.logger.info(f"Initialized super rate limiter with {max_rpm} requests per minute")
    

    async def send_request(self, body):
        """
        Send a request to the Router API with rate limiting.
        """
        model = body.get('model', 'unknown')
        timeout = aiohttp.ClientTimeout(total=300) # 5 minutes
        self.logger.debug(f"Sending request to Router for model {model}")
        
        try:
            # Apply super rate limiter before making the request
            self.logger.debug(f"Waiting for super rate limiter ({self.max_rpm} rpm)")
            async with self._super_limiter:
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
            self.logger.error(f"Error in API response for model {model}: {response_data}")
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