"""Build script to convert SQLite database to JSON for Vercel deployment."""

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

from chess_llm_eval.data.json_repo import JSONRepository
from chess_llm_eval.schemas import AnalyticsResponse
from website.server.analytics import build_analytics_response


def convert_sqlite_to_json(
    db_path: str = "data/storage.db",
    output_path: str = "data.json",
    validate: bool = False,
) -> None:
    """Convert SQLite database to JSON format for serverless deployment.

    This script runs during Vercel build time, not at runtime.
    The generated JSON file is included in the deployment bundle.

    Args:
        db_path: Path to the SQLite database file
        output_path: Path to write the JSON output
    """
    print(f"Converting {db_path} to JSON...")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Export each table
    tables = ["puzzle", "agent", "game", "move", "benchmark"]
    data: dict[str, Any] = {}

    for table in tables:
        print(f"  Exporting {table}...")
        cursor = conn.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()

        # Convert rows to dicts
        columns = [description[0] for description in cursor.description]
        data[table] = [dict(zip(columns, row, strict=False)) for row in rows]

        print(f"    - {len(data[table])} rows exported")

    # Also export pre-computed analytics for better performance
    print("  Computing analytics...")
    data["analytics"] = compute_analytics(conn)

    # Write to JSON
    print(f"  Writing to {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    # Verify file was created
    output_file = Path(output_path)
    if output_file.exists():
        size_mb = output_file.stat().st_size / (1024 * 1024)
        print(f"SUCCESS: Conversion complete! JSON size: {size_mb:.2f} MB")
    else:
        print("ERROR: Output file was not created!")
        sys.exit(1)

    conn.close()

    if validate:
        validate_json_output(output_path)


def validate_json_output(output_path: str) -> None:
    """Validate generated JSON against API schemas."""
    print("  Validating JSON output against schemas...")
    repository = JSONRepository(output_path)
    response = build_analytics_response(repository)
    AnalyticsResponse.model_validate(response.model_dump())
    print("  Schema validation passed.")


def compute_analytics(conn: sqlite3.Connection) -> dict[str, Any]:
    """Pre-compute expensive analytics queries at build time."""
    analytics = {}

    # Leaderboard data
    cursor = conn.execute("""
        SELECT
            a.name,
            a.rating,
            a.rd,
            COUNT(g.id) as games_played,
            SUM(CASE WHEN g.failed = 0 THEN 1 ELSE 0 END) as wins,
            1.0 * SUM(CASE WHEN g.failed = 0 THEN 1 ELSE 0 END) / COUNT(g.id)
            as win_rate
        FROM agent a
        LEFT JOIN game g ON a.name = g.agent_name
        GROUP BY a.name
        ORDER BY a.rating DESC
    """)
    analytics["leaderboard"] = [dict(row) for row in cursor.fetchall()]

    # Rating trends (last 50 games per agent)
    cursor = conn.execute("""
        SELECT
            b.id,
            g.agent_name,
            b.agent_rating,
            b.agent_deviation,
            ROW_NUMBER() OVER (
                PARTITION BY g.agent_name ORDER BY g.date
            ) as game_number
        FROM benchmark b
        JOIN game g ON b.game_id = g.id
        ORDER BY g.agent_name, game_number
    """)
    analytics["rating_trends"] = [dict(row) for row in cursor.fetchall()]

    # Puzzle outcomes by type
    cursor = conn.execute("""
        SELECT
            p.type,
            SUM(CASE WHEN g.failed = 0 THEN 1 ELSE 0 END) as successes,
            SUM(CASE WHEN g.failed = 1 THEN 1 ELSE 0 END) as failures
        FROM puzzle p
        JOIN game g ON p.id = g.puzzle_id
        GROUP BY p.type
    """)
    analytics["puzzle_outcomes"] = [dict(row) for row in cursor.fetchall()]

    # Illegal moves count per agent
    cursor = conn.execute("""
        SELECT
            g.agent_name,
            SUM(CASE WHEN m.illegal_move = 1 THEN 1 ELSE 0 END) as illegal_moves_count,
            COUNT(m.id) as total_moves
        FROM game g
        JOIN move m ON g.id = m.game_id
        GROUP BY g.agent_name
    """)
    analytics["illegal_moves"] = [dict(row) for row in cursor.fetchall()]

    # Token usage stats
    cursor = conn.execute("""
        SELECT
            g.agent_name,
            AVG(m.prompt_tokens) as avg_puzzle_prompt_tokens,
            AVG(m.completion_tokens) as avg_puzzle_completion_tokens
        FROM game g
        JOIN move m ON g.id = m.game_id
        GROUP BY g.agent_name
    """)
    analytics["token_usage"] = [dict(row) for row in cursor.fetchall()]

    return analytics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build JSON data for Vercel deployment.")
    parser.add_argument("--db-path", default="data/storage.db")
    parser.add_argument("--output-path", default="data.json")
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate JSON output against API schemas.",
    )
    args = parser.parse_args()

    convert_sqlite_to_json(
        db_path=args.db_path,
        output_path=args.output_path,
        validate=args.validate,
    )
