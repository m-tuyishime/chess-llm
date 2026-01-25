from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class HealthResponse(BaseSchema):
    """Response schema for health check."""

    status: str


class PuzzleResponse(BaseSchema):
    id: str
    fen: str
    moves: str
    rating: int
    rating_deviation: int
    themes: str | None = None
    type: str
    popularity: int
    nb_plays: int
    game_url: str | None = None
    opening_tags: str | None = None


class MoveRecordResponse(BaseSchema):
    fen: str
    expected_move: str
    actual_move: str
    is_illegal: bool
    prompt_tokens: int
    completion_tokens: int
    game_id: int | None = None
    id: int | None = None


class GameResponse(BaseSchema):
    id: int | None
    puzzle_id: str
    puzzle_type: str
    agent_name: str
    failed: bool
    moves: list[MoveRecordResponse] = Field(default_factory=list)
    date: datetime


class AgentRankingResponse(BaseSchema):
    name: str
    rating: float
    rd: float
    win_rate: float
    games_played: int


class AgentDetailResponse(BaseSchema):
    name: str
    is_reasoning: bool
    is_random: bool
    rating: float
    rd: float
    volatility: float
    games: list[GameResponse] = Field(default_factory=list)
