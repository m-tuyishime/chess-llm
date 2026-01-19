from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from chess_llm_eval.data.protocols import GameRepository
from chess_llm_eval.schemas import (
    AgentDetailResponse,
    AgentRankingResponse,
    GameResponse,
    HealthResponse,
    PuzzleResponse,
)
from website.server.dependencies import get_repository

app = FastAPI(title="Chess-LLM Arena API")

# Configure CORS for portfolio subdomain (and local dev)
# TODO: Move to config
origins = [
    "http://localhost:5173",  # Vite default
    "http://localhost:5174",
    "http://localhost:3000",
    # Add production domain later
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/api/leaderboard", response_model=list[AgentRankingResponse])
async def get_leaderboard(
    repository: Annotated[GameRepository, Depends(get_repository)],
) -> list[AgentRankingResponse]:
    """Get the leaderboard of agents."""
    return [AgentRankingResponse.model_validate(r) for r in repository.get_leaderboard()]


@app.get("/api/agents/{name:path}", response_model=AgentDetailResponse)
async def get_agent_detail(
    name: str, repository: Annotated[GameRepository, Depends(get_repository)]
) -> AgentDetailResponse:
    """Get detailed statistics for a specific agent."""
    agent = repository.get_agent(name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    games = repository.get_agent_games(name)

    # We construct the response explicitly because AgentData doesn't have 'games'
    return AgentDetailResponse(
        name=agent.name,
        is_reasoning=agent.is_reasoning,
        is_random=agent.is_random,
        rating=agent.rating,
        rd=agent.rd,
        volatility=agent.volatility,
        games=[GameResponse.model_validate(g) for g in games],
    )


@app.get("/api/games/{idstr}", response_model=GameResponse)
async def get_game(
    idstr: str, repository: Annotated[GameRepository, Depends(get_repository)]
) -> GameResponse:
    """
    Get a game's details by ID.
    Note: ID is int in DB but potentially passed as string.
    """
    try:
        game_id = int(idstr)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid game ID format") from None

    game = repository.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    return GameResponse.model_validate(game)


@app.get("/api/puzzles/{id}", response_model=PuzzleResponse)
async def get_puzzle(
    id: str, repository: Annotated[GameRepository, Depends(get_repository)]
) -> PuzzleResponse:
    """Get puzzle metadata."""
    puzzle = repository.get_puzzle(id)
    if not puzzle:
        raise HTTPException(status_code=404, detail="Puzzle not found")

    return PuzzleResponse.model_validate(puzzle)
