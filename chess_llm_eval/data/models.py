from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Puzzle:
    id: str
    fen: str
    moves: str  # Space-separated UCI moves
    rating: int
    rating_deviation: int
    themes: str
    type: str
    popularity: int = 0
    nb_plays: int = 0
    game_url: str = ""
    opening_tags: str = ""


@dataclass
class AgentData:
    name: str
    is_reasoning: bool
    is_random: bool
    rating: float = 1500.0
    rd: float = 350.0
    volatility: float = 0.06


@dataclass
class MoveRecord:
    fen: str
    expected_move: str
    actual_move: str
    is_illegal: bool
    prompt_tokens: int = 0
    completion_tokens: int = 0
    game_id: int | None = None
    id: int | None = None


@dataclass
class Game:
    puzzle_id: str
    agent_name: str
    failed: bool
    moves: list[MoveRecord] = field(default_factory=list)
    id: int | None = None
    date: datetime = field(default_factory=datetime.now)
    puzzle_type: str = ""


@dataclass
class AgentRanking:
    name: str
    rating: float
    rd: float
    win_rate: float
    games_played: int
