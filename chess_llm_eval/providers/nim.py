import asyncio
import logging
import os
import random
import traceback
from datetime import datetime
from typing import Any, cast

from aiolimiter import AsyncLimiter
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

logger = logging.getLogger(__name__)


class NIMProvider:  # Implements LLMProvider via Protocol
    """LLM Provider implementation for NVIDIA NIM."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        max_rpm: int = 100,
    ) -> None:
        self.api_key = api_key or os.getenv("NIM_API_KEY")
        if not self.api_key:
            raise ValueError("NIM_API_KEY not provided and not found in environment")

        self.base_url = base_url
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=self.api_key,
        )
        self.max_rpm = max_rpm
        self._super_limiter = AsyncLimiter(max_rpm, time_period=60)
        logger.info(f"Initialized NIM provider with {max_rpm} requests per minute")

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> tuple[str, int, int]:
        """
        Send a completion request to the LLM.
        """
        start_time = datetime.now()
        logger.debug(f"Waiting for rate limiter ({self.max_rpm} rpm)")

        try:
            async with self._super_limiter:
                # Reduced sleep for efficiency, but kept to smooth out bursts
                await asyncio.sleep(random.uniform(0, 0.5))

                completion = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,  # type: ignore
                    temperature=temperature,
                    stream=False,
                    max_tokens=max_tokens,
                    **kwargs,
                )
                completion = cast(ChatCompletion, completion)

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.debug(f"Received response for {model} in {elapsed:.2f}s")

            if not completion or not completion.choices:
                raise ValueError("Empty response from API")

            choice = completion.choices[0]
            content = choice.message.content or ""

            usage = completion.usage
            pt = usage.prompt_tokens if usage else 0
            ct = usage.completion_tokens if usage else 0

            return content, pt, ct

        except Exception as e:
            logger.error(f"Error during API request for model {model}: {e}")
            logger.debug(traceback.format_exc())
            raise
