from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from chess_llm_eval.data.protocols import GameRepository
from chess_llm_eval.schemas import (
    AgentDetailResponse,
    AgentPuzzleOutcomeResponse,
    AgentRankingResponse,
    AnalyticsResponse,
    GameResponse,
    GameSummaryResponse,
    HealthResponse,
    PuzzleResponse,
)
from website.server.dependencies import get_repository

app = FastAPI(title="Chess-LLM Arena API")

# Configure CORS for portfolio subdomain (and local dev)
origins = [
    "http://localhost:5173",  # Vite default
    "http://localhost:5174",
    "http://localhost:3000",
    "http://localhost:4000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:4000",
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


@app.get("/api/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    repository: Annotated[GameRepository, Depends(get_repository)],
) -> AnalyticsResponse:
    """Get aggregate analytics for all agents."""
    # Benchmarks (Rating trends)
    bench_df = repository.get_benchmark_data()
    if not bench_df.empty:
        # Convert Timestamp to string or ensure it's JSON serializable
        bench_df["date"] = bench_df["date"].dt.strftime("%Y-%m-%dT%H:%M:%S")
        rating_trends = bench_df.to_dict("records")
    else:
        rating_trends = []

    # Puzzle outcomes
    outcome_df = repository.get_puzzle_outcome_data()
    puzzle_outcomes = outcome_df.to_dict("records") if not outcome_df.empty else []

    # Illegal moves
    illegal_df = repository.get_illegal_moves_data()
    if not illegal_df.empty:
        illegal_df["illegal_percentage"] = (
            illegal_df["illegal_moves_count"] / illegal_df["total_moves"]
        ) * 100
        illegal_moves = illegal_df.to_dict("records")
    else:
        illegal_moves = []

    # Token usage
    token_df = repository.get_token_usage_per_puzzle_data()
    if not token_df.empty:
        token_df = token_df.rename(
            columns={
                "avg_puzzle_prompt_tokens": "avg_prompt_tokens",
                "avg_puzzle_completion_tokens": "avg_completion_tokens",
            }
        )
        token_usage = token_df.to_dict("records")
    else:
        token_usage = []

    # Final ratings and intervals
    final_ratings_df = repository.get_final_ratings_data()
    if not final_ratings_df.empty:
        final_ratings_df["error"] = final_ratings_df["agent_deviation"] * 2
        final_ratings = final_ratings_df.to_dict("records")
    else:
        final_ratings = []

    weighted_rating, weighted_rd = repository.get_weighted_puzzle_rating()

    return AnalyticsResponse(
        rating_trends=rating_trends,
        puzzle_outcomes=puzzle_outcomes,
        illegal_moves=illegal_moves,
        token_usage=token_usage,
        final_ratings=final_ratings,
        weighted_puzzle_rating=weighted_rating,
        weighted_puzzle_deviation=weighted_rd,
    )


@app.get("/api/analytics/agents/{name:path}", response_model=list[AgentPuzzleOutcomeResponse])
async def get_agent_analytics(
    name: str, repository: Annotated[GameRepository, Depends(get_repository)]
) -> list[AgentPuzzleOutcomeResponse]:
    """Get detailed analytics for a specific agent."""
    df = repository.get_puzzle_outcomes_by_agent_data()
    if df.empty:
        return []

    agent_df = df[df["agent_name"] == name]
    return [AgentPuzzleOutcomeResponse.model_validate(row) for _, row in agent_df.iterrows()]


@app.get("/api/agents/{name:path}", response_model=AgentDetailResponse)
async def get_agent_detail(
    name: str, repository: Annotated[GameRepository, Depends(get_repository)]
) -> AgentDetailResponse:
    """Get detailed statistics for a specific agent."""
    agent = repository.get_agent(name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    games = repository.get_agent_games(name)

    return AgentDetailResponse(
        name=agent.name,
        is_reasoning=agent.is_reasoning,
        is_random=agent.is_random,
        rating=agent.rating,
        rd=agent.rd,
        volatility=agent.volatility,
        games=[
            GameSummaryResponse(
                id=g.id,
                puzzle_id=g.puzzle_id,
                puzzle_type=g.puzzle_type,
                agent_name=g.agent_name,
                failed=g.failed,
                move_count=g.move_count,
                date=g.date,
            )
            for g in games
        ],
    )


@app.get("/api/games/{idstr}", response_model=GameResponse)
async def get_game(
    idstr: str, repository: Annotated[GameRepository, Depends(get_repository)]
) -> GameResponse:
    """Get a game's details by ID."""
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
