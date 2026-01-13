import logging
import re
from typing import Any

from chess_llm_eval.agents.base import Agent
from chess_llm_eval.core.types import Color, Fen, SanMove
from chess_llm_eval.providers.base import LLMProvider

logger = logging.getLogger(__name__)


class LLMAgent(Agent):
    """Agent that uses an LLM via the LLMProvider interface."""

    def __init__(
        self, provider: LLMProvider, model_name: str, is_reasoning: bool = False, **kwargs: Any
    ) -> None:
        super().__init__(model_name, is_reasoning=is_reasoning, **kwargs)
        self.provider = provider

    def _create_messages(
        self, fen: Fen, legal_moves: list[SanMove], color: Color
    ) -> list[dict[str, str]]:
        system_prompt = (
            f"You are a chess engine playing as {color}. "
            "You will be provided with a FEN string and a list of legal moves. "
            "Analyze the position deeply, considering tactics, strategy, and endgames. "
            "Think step-by-step. "
            "Finally, output your chosen move inside <FinalMove> tags. "
            "Example: <FinalMove>e4</FinalMove>"
        )

        user_prompt = f"FEN: {fen}\nLegal Moves: {', '.join(legal_moves)}"

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _parse_move(self, content: str) -> SanMove | None:
        # Try to find <FinalMove> tag
        match = re.search(r"<FinalMove>(.*?)</FinalMove>", content, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # Fallback: if message is short and looks like a move, take it?
        # But safest is to require tag, or maybe last word if strictly one word?
        # Let's stick to tag based on retry logic seen earlier.
        # But maybe fallback to just the content if it matches a move pattern?
        # For now, strict extraction to avoid hallucination interpretation.
        return None

    async def get_move(
        self, fen: Fen, legal_moves: list[SanMove], color: Color
    ) -> tuple[SanMove, int, int] | None:
        messages = self._create_messages(fen, legal_moves, color)

        try:
            content, pt, ct = await self.provider.complete(
                messages,
                model=self.model_name,
                temperature=0.2,  # low temp for stability
            )

            move = self._parse_move(content)
            if not move:
                logger.warning(f"Failed to parse move from content: {content[:100]}...")
                return None

            # Clean move string (remove punctuation etc)
            move = move.replace(".", "").replace(" ", "").strip()

            return move, pt, ct

        except Exception as e:
            logger.error(f"Error getting move from LLM: {e}")
            return None

    async def retry_move(
        self, failed_moves: list[SanMove], fen: Fen, legal_moves: list[SanMove], color: Color
    ) -> tuple[SanMove, int, int] | None:
        messages = self._create_messages(fen, legal_moves, color)

        # Append history of failures
        # Note: most providers are stateless per request, so we build full history
        for bad_move in failed_moves:
            messages.append({"role": "assistant", "content": f"<FinalMove>{bad_move}</FinalMove>"})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"The move {bad_move} is illegal or invalid. "
                        f"Please choose a legal move from the list: {', '.join(legal_moves)}. "
                        "Wrap it in <FinalMove> tags."
                    ),
                }
            )

        try:
            content, pt, ct = await self.provider.complete(
                messages,
                model=self.model_name,
                temperature=0.4,  # higher temp for retry
            )

            move = self._parse_move(content)
            if not move:
                return None

            move = move.replace(".", "").replace(" ", "").strip()
            return move, pt, ct

        except Exception as e:
            logger.error(f"Error retrying move: {e}")
            return None
