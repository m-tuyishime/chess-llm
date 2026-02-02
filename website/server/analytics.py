from typing import Any, cast

import pandas as pd

from chess_llm_eval.data.protocols import GameRepository
from chess_llm_eval.schemas import AnalyticsResponse


def build_analytics_response(repository: GameRepository) -> AnalyticsResponse:
    """Build analytics response data from repository."""
    bench_df = repository.get_benchmark_data()
    if not bench_df.empty:
        # Downsample if too many points to improve frontend performance
        # Target ~500 points per agent max
        max_points_per_agent = 500

        downsampled_parts = []
        for _, group in bench_df.groupby("agent_name"):
            n = len(group)
            if n > max_points_per_agent:
                step = n // max_points_per_agent
                # Always include the last point to show the final rating accurately
                downsampled_group = group.iloc[::step].copy()
                last_row = group.iloc[[-1]]
                if not last_row.index.isin(downsampled_group.index).all():
                    downsampled_group = pd.concat([downsampled_group, last_row])
                downsampled_parts.append(downsampled_group)
            else:
                downsampled_parts.append(group)

        if downsampled_parts:
            bench_df = pd.concat(downsampled_parts).sort_values(["agent_name", "evaluation_index"])

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
        rating_trends=cast(Any, rating_trends),
        puzzle_outcomes=cast(Any, puzzle_outcomes),
        illegal_moves=cast(Any, illegal_moves),
        token_usage=cast(Any, token_usage),
        final_ratings=cast(Any, final_ratings),
        weighted_puzzle_rating=weighted_rating,
        weighted_puzzle_deviation=weighted_rd,
    )
