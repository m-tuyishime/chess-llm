"""JSON-based repository implementation for serverless deployment.

This module provides a read-only repository that loads data from JSON files,
designed for Vercel serverless functions where SQLite is problematic.
"""

import json
import logging
from pathlib import Path

import pandas as pd

from chess_llm_eval.data.models import AgentData, AgentRanking, Game, MoveRecord, Puzzle
from chess_llm_eval.data.protocols import GameRepository

logger = logging.getLogger(__name__)


class JSONRepository(GameRepository):
    """JSON-based implementation of GameRepository for read-only serverless deployment.

    This repository loads all data from a JSON file at initialization and uses
    Pandas DataFrames for efficient querying. It's designed for Vercel's serverless
    environment where file system limitations make SQLite impractical.

    All data is loaded into memory at startup, providing fast read access but
    higher memory usage than SQLite.

    Example:
        repo = JSONRepository("data.json")
        puzzles = repo.get_puzzles(limit=10)
        agent = repo.get_agent("gpt-4o")
    """

    def __init__(self, json_path: str = "data.json") -> None:
        """Initialize repository from JSON file.

        Args:
            json_path: Path to the JSON data file. Can be absolute or relative
                      to the current working directory.

        Raises:
            FileNotFoundError: If the JSON file does not exist.
            json.JSONDecodeError: If the JSON file is malformed.
        """
        self.json_path = Path(json_path)
        logger.info(f"Loading data from {self.json_path}")

        # Load JSON data
        with open(self.json_path, encoding="utf-8") as f:
            data = json.load(f)

        # Convert to DataFrames for efficient querying
        self.puzzles_df = pd.DataFrame(data["puzzle"])
        self.agents_df = pd.DataFrame(data["agent"])
        self.games_df = pd.DataFrame(data["game"])
        self.moves_df = pd.DataFrame(data["move"])
        self.benchmarks_df = pd.DataFrame(data["benchmark"])

        # Pre-computed analytics (optional, for better performance)
        self.analytics = data.get("analytics", {})

        # Build lookup indexes for O(1) access
        self.puzzle_by_id = {p["id"]: p for p in data["puzzle"]}
        self.agent_by_name = {a["name"]: a for a in data["agent"]}

        logger.info(
            f"Loaded: {len(self.puzzles_df)} puzzles, "
            f"{len(self.agents_df)} agents, "
            f"{len(self.games_df)} games, "
            f"{len(self.moves_df)} moves"
        )

    def get_puzzles(self, limit: int | None = None) -> list[Puzzle]:
        """Get puzzles, optionally limited.

        Args:
            limit: Maximum number of puzzles to return. If None, returns all.

        Returns:
            List of Puzzle objects.
        """
        df = self.puzzles_df.head(limit) if limit else self.puzzles_df
        return [Puzzle(**row) for _, row in df.iterrows()]

    def get_puzzle(self, puzzle_id: str) -> Puzzle | None:
        """Get a single puzzle by ID.

        Args:
            puzzle_id: The puzzle identifier.

        Returns:
            Puzzle object or None if not found.
        """
        puzzle = self.puzzle_by_id.get(puzzle_id)
        return Puzzle(**puzzle) if puzzle else None

    def get_uncompleted_puzzles(self, agent_name: str, limit: int | None = None) -> list[Puzzle]:
        """Get puzzles not yet attempted by an agent.

        Args:
            agent_name: Name of the agent.
            limit: Maximum number of puzzles to return.

        Returns:
            List of Puzzle objects not yet attempted.
        """
        # Get puzzles already attempted by this agent
        attempted = self.games_df[self.games_df["agent_name"] == agent_name]["puzzle_id"].unique()

        # Filter puzzles
        uncompleted = self.puzzles_df[~self.puzzles_df["id"].isin(attempted)]
        if limit:
            uncompleted = uncompleted.head(limit)

        return [Puzzle(**row) for _, row in uncompleted.iterrows()]

    def get_agent(self, name: str) -> AgentData | None:
        """Get agent data by name.

        Args:
            name: Agent name.

        Returns:
            AgentData object or None if not found.
        """
        agent = self.agent_by_name.get(name)
        if not agent:
            return None

        # Get latest benchmark if available
        benchmarks = self.benchmarks_df.merge(
            self.games_df[["id", "agent_name"]], left_on="game_id", right_on="id"
        )
        latest = (
            benchmarks[benchmarks["agent_name"] == name]
            .sort_values("game_id", ascending=False)
            .head(1)
        )

        if not latest.empty:
            agent = agent.copy()
            agent["rating"] = latest.iloc[0]["agent_rating"]
            agent["rd"] = latest.iloc[0]["agent_deviation"]

        # Map field names from JSON to AgentData model
        agent["is_reasoning"] = agent.pop("reasoning", agent.get("is_reasoning", False))
        agent["is_random"] = agent.pop("random", agent.get("is_random", False))

        return AgentData(**agent)

    def get_all_agents(self) -> list[AgentData]:
        """Get all agents.

        Returns:
            List of AgentData objects with latest ratings.
        """
        agents = []
        for _, agent_row in self.agents_df.iterrows():
            agent = agent_row.to_dict()

            # Get latest benchmark
            benchmarks = self.benchmarks_df.merge(
                self.games_df[["id", "agent_name"]], left_on="game_id", right_on="id"
            )
            latest = (
                benchmarks[benchmarks["agent_name"] == agent["name"]]
                .sort_values("game_id", ascending=False)
                .head(1)
            )

            if not latest.empty:
                agent["rating"] = latest.iloc[0]["agent_rating"]
                agent["rd"] = latest.iloc[0]["agent_deviation"]

            # Map field names from JSON to AgentData model
            agent["is_reasoning"] = agent.pop("reasoning", agent.get("is_reasoning", False))
            agent["is_random"] = agent.pop("random", agent.get("is_random", False))

            agents.append(AgentData(**agent))  # type: ignore[misc]

        return agents

    def get_last_benchmark(self, agent_name: str) -> tuple[float, float, float] | None:
        """Get the last benchmark rating for an agent.

        Args:
            agent_name: Name of the agent.

        Returns:
            Tuple of (rating, deviation, volatility) or None.
        """
        benchmarks = self.benchmarks_df.merge(
            self.games_df[["id", "agent_name"]], left_on="game_id", right_on="id"
        )
        latest = (
            benchmarks[benchmarks["agent_name"] == agent_name]
            .sort_values("game_id", ascending=False)
            .head(1)
        )

        if latest.empty:
            return None

        return (
            latest.iloc[0]["agent_rating"],
            latest.iloc[0]["agent_deviation"],
            latest.iloc[0]["agent_volatility"],
        )

    def get_game(self, game_id: int) -> Game | None:
        """Get a game by ID with all moves.

        Args:
            game_id: Game identifier.

        Returns:
            Game object with moves or None if not found.
        """
        game_row = self.games_df[self.games_df["id"] == game_id]
        if game_row.empty:
            return None

        game = game_row.iloc[0].to_dict()

        # Get moves for this game
        moves = self.moves_df[self.moves_df["game_id"] == game_id]
        game["moves"] = [MoveRecord(**row) for _, row in moves.iterrows()]

        return Game(**game)  # type: ignore[misc]

    def get_agent_games(self, agent_name: str) -> list[Game]:
        """Get all games for an agent (without move details).

        Args:
            agent_name: Name of the agent.

        Returns:
            List of Game objects.
        """
        games = self.games_df[self.games_df["agent_name"] == agent_name]
        return [Game(**row) for _, row in games.iterrows()]

    def get_leaderboard(self) -> list[AgentRanking]:
        """Get leaderboard data.

        Returns:
            List of AgentRanking objects sorted by rating.
        """
        if "leaderboard" in self.analytics:
            # Use pre-computed analytics
            return [
                AgentRanking(
                    name=item["name"],
                    rating=item["rating"],
                    rd=item["rd"],
                    win_rate=item.get("win_rate", 0.0),
                    games_played=item.get("games_played", 0),
                )
                for item in self.analytics["leaderboard"]
            ]

        # Compute on-the-fly
        rankings = []
        for agent_name in self.agents_df["name"]:
            games = self.games_df[self.games_df["agent_name"] == agent_name]
            if games.empty:
                continue

            total = len(games)
            wins = len(games[games["failed"] == 0])
            win_rate = (wins / total * 100) if total > 0 else 0.0

            # Get latest rating
            latest = self.get_last_benchmark(agent_name)
            rating = latest[0] if latest else 1500.0
            rd = latest[1] if latest else 350.0

            rankings.append(
                AgentRanking(
                    name=agent_name,
                    rating=rating,
                    rd=rd,
                    win_rate=round(win_rate, 2),
                    games_played=total,
                )
            )

        return sorted(rankings, key=lambda x: x.rating, reverse=True)

    def get_benchmark_data(self) -> pd.DataFrame:
        """Get benchmark data as DataFrame."""
        merged = self.benchmarks_df.merge(
            self.games_df[["id", "agent_name", "date"]],
            left_on="game_id",
            right_on="id",
        )
        merged = merged.sort_values("id_x").copy()
        merged["evaluation_index"] = merged.groupby("agent_name").cumcount() + 1
        merged["date"] = pd.to_datetime(merged["date"], errors="coerce")
        return merged

    def get_puzzle_outcome_data(self) -> pd.DataFrame:
        """Get puzzle outcome data."""
        if "puzzle_outcomes" in self.analytics:
            return pd.DataFrame(self.analytics["puzzle_outcomes"])

        return (
            self.games_df.merge(
                self.puzzles_df[["id", "type"]],
                left_on="puzzle_id",
                right_on="id",
            )
            .groupby("type")
            .agg({"failed": ["count", "sum"]})
            .reset_index()
        )

    def get_puzzle_outcome_data_by_agent(self) -> pd.DataFrame:
        """Get puzzle outcome data grouped by agent."""
        return (
            self.games_df.merge(
                self.puzzles_df[["id", "type"]],
                left_on="puzzle_id",
                right_on="id",
            )
            .groupby(["agent_name", "type"])
            .agg({"failed": ["count", "sum"]})
            .reset_index()
        )

    def get_illegal_moves_data(self) -> pd.DataFrame:
        """Get illegal moves data."""
        if "illegal_moves" in self.analytics:
            df = pd.DataFrame(self.analytics["illegal_moves"])
            if "illegal_count" in df.columns and "illegal_moves_count" not in df.columns:
                df = df.rename(columns={"illegal_count": "illegal_moves_count"})
            return df

        return (
            self.moves_df.merge(
                self.games_df[["id", "agent_name"]],
                left_on="game_id",
                right_on="id",
            )
            .groupby("agent_name")
            .agg(
                illegal_moves_count=("illegal_move", "sum"),
                total_moves=("illegal_move", "count"),
            )
            .reset_index()
        )

    def get_final_ratings_data(self) -> pd.DataFrame:
        """Get final ratings data."""
        return (
            self.get_benchmark_data()
            .sort_values("game_id")
            .groupby("agent_name")
            .last()[["agent_rating", "agent_deviation", "agent_volatility"]]
            .reset_index()
        )

    def get_weighted_puzzle_rating(self) -> tuple[float, float]:
        """Get weighted average puzzle rating."""
        attempted_puzzles = self.games_df["puzzle_id"].unique()
        attempted_df = self.puzzles_df[self.puzzles_df["id"].isin(attempted_puzzles)]

        if attempted_df.empty:
            return (0.0, 0.0)

        avg_rating = attempted_df["rating"].mean()
        avg_deviation = attempted_df["rating_deviation"].mean()

        return (float(avg_rating), float(avg_deviation))

    def get_solutionary_agent_moves(self) -> pd.DataFrame:
        """Get solution vs actual moves data."""
        return (
            self.moves_df.merge(
                self.games_df[["id", "agent_name"]],
                left_on="game_id",
                right_on="id",
            )
            .groupby("agent_name")
            .apply(
                lambda x: pd.Series(
                    {
                        "correct_moves": (x["move"] == x["correct_move"]).sum(),
                        "total_moves": len(x),
                    }
                )
            )
            .reset_index()
        )

    def get_token_usage_per_move_data(self) -> pd.DataFrame:
        """Get token usage per move."""
        if "token_usage" in self.analytics:
            df = pd.DataFrame(self.analytics["token_usage"])
            if "avg_prompt_tokens" not in df.columns and "avg_puzzle_prompt_tokens" in df.columns:
                df = df.rename(
                    columns={
                        "avg_puzzle_prompt_tokens": "avg_prompt_tokens",
                        "avg_puzzle_completion_tokens": "avg_completion_tokens",
                    }
                )
            return df

        return (
            self.moves_df.merge(
                self.games_df[["id", "agent_name"]],
                left_on="game_id",
                right_on="id",
            )
            .groupby("agent_name")
            .agg({"prompt_tokens": "mean", "completion_tokens": "mean"})
            .reset_index()
        )

    def get_token_usage_per_puzzle_data(self) -> pd.DataFrame:
        """Get token usage per puzzle."""
        if "token_usage" in self.analytics:
            df = pd.DataFrame(self.analytics["token_usage"])
            if "avg_puzzle_prompt_tokens" not in df.columns and "avg_prompt_tokens" in df.columns:
                df = df.rename(
                    columns={
                        "avg_prompt_tokens": "avg_puzzle_prompt_tokens",
                        "avg_completion_tokens": "avg_puzzle_completion_tokens",
                    }
                )
            return df

        return (
            self.moves_df.merge(
                self.games_df[["id", "agent_name", "puzzle_id"]],
                left_on="game_id",
                right_on="id",
            )
            .groupby(["agent_name", "puzzle_id"])
            .agg({"prompt_tokens": "sum", "completion_tokens": "sum"})
            .groupby("agent_name")
            .mean()
            .reset_index()
            .rename(
                columns={
                    "prompt_tokens": "avg_puzzle_prompt_tokens",
                    "completion_tokens": "avg_puzzle_completion_tokens",
                }
            )
        )

    def get_solutionary_moves_data(self) -> pd.DataFrame:
        """Get detailed solutionary moves data."""
        return (
            self.moves_df[self.moves_df["illegal_move"] == 0]
            .merge(
                self.games_df[["id", "agent_name"]],
                left_on="game_id",
                right_on="id",
            )
            .groupby(["agent_name", "correct_move"])
            .agg({"move": lambda x: (x == x.name).sum()})  # type: ignore[misc]
            .reset_index()
        )

    def save_agent(self, agent: AgentData) -> None:
        """Not supported in read-only JSON mode."""
        raise NotImplementedError("JSONRepository is read-only")

    def get_puzzle_outcomes_by_agent_data(self) -> pd.DataFrame:
        """
        Retrieve puzzle outcomes grouped by agent and puzzle type.
        Returns columns: agent_name, type, successes, failures.
        """
        # Merge games with puzzles to get puzzle type
        merged = self.games_df.merge(
            self.puzzles_df[["id", "type"]],
            left_on="puzzle_id",
            right_on="id",
        )

        # Group by agent_name and type, count successes and failures
        return (
            merged.groupby(["agent_name", "type"])
            .agg(
                successes=("failed", lambda x: (x == 0).sum()),
                failures=("failed", lambda x: (x == 1).sum()),
            )
            .reset_index()
        )

    # Write operations - not supported in read-only JSON mode
    def save_puzzles(self, puzzles: list[Puzzle]) -> None:
        """Not supported in read-only JSON mode."""
        raise NotImplementedError("JSONRepository is read-only")

    def create_game(self, puzzle_id: str, agent_name: str) -> int:
        """Not supported in read-only JSON mode."""
        raise NotImplementedError("JSONRepository is read-only")

    def save_move(self, game_id: int, move: MoveRecord) -> None:
        """Not supported in read-only JSON mode."""
        raise NotImplementedError("JSONRepository is read-only")

    def update_game_result(self, game_id: int, failed: bool) -> None:
        """Not supported in read-only JSON mode."""
        raise NotImplementedError("JSONRepository is read-only")

    def save_benchmark(
        self,
        game_id: int,
        rating: float,
        rd: float,
        volatility: float,
    ) -> None:
        """Not supported in read-only JSON mode."""
        raise NotImplementedError("JSONRepository is read-only")
