import asyncio
import logging
import random
import traceback
from datetime import datetime
from typing import Any, cast

from aiolimiter import AsyncLimiter
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

logger = logging.getLogger(__name__)


class OpenRouterProvider:  # Implements LLMProvider via Protocol
    """LLM Provider implementation for OpenRouter."""

    def __init__(self, base_url: str, api_key: str, max_rpm: int = 100) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
        )
        self.max_rpm = max_rpm
        self._super_limiter = AsyncLimiter(max_rpm, time_period=60)
        logger.info(f"Initialized OpenRouter provider with {max_rpm} requests per minute")

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

                # Prepare extra_body for OpenRouter specific features
                extra_body = kwargs.get("extra_body", {})
                if "include_usage" not in extra_body:
                    extra_body["include_usage"] = True

                # Filter kwargs for standard params
                api_kwargs = {k: v for k, v in kwargs.items() if k not in ["extra_body"]}

                completion = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,  # type: ignore
                    temperature=temperature,
                    stream=False,
                    extra_body=extra_body,
                    max_tokens=max_tokens,
                    **api_kwargs,
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
