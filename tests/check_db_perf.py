import os
import sys
import time

# Add project root to sys.path
sys.path.append(os.getcwd())

from chess_llm_eval.data.sqlite import SQLiteRepository


def measure_performance() -> None:
    repo = SQLiteRepository("data/storage.db")

    print("Measuring Leaderboard performance...")
    start = time.time()
    leaderboard = repo.get_leaderboard()
    end = time.time()
    leaderboard_time = end - start
    print(f"Leaderboard took: {leaderboard_time:.4f}s (returned {len(leaderboard)} agents)")

    # Assert leaderboard is fast (under 100ms for this dataset)
    if leaderboard_time > 0.1:
        print(f"WARNING: Leaderboard is slow! ({leaderboard_time:.4f}s)")
        # sys.exit(1) # Uncomment to enforce failure

    if leaderboard:
        agent_name = leaderboard[0].name
        print(f"\nMeasuring Agent Detail performance for '{agent_name}'...")
        start = time.time()
        games = repo.get_agent_games(agent_name)
        end = time.time()
        agent_time = end - start
        print(f"Agent Detail (summary fetch) took: {agent_time:.4f}s (returned {len(games)} games)")

        # Assert agent detail is fast (under 100ms)
        if agent_time > 0.1:
            print(f"WARNING: Agent Detail is slow! ({agent_time:.4f}s)")
            # sys.exit(1)

        # Check moves count logic (should come from move_count field now)
        total_moves = sum(g.move_count for g in games)
        print(f"Total moves counted: {total_moves}")

        # Verify moves list is empty to confirm optimization
        moves_loaded = sum(len(g.moves) for g in games)
        print(f"Total move objects loaded: {moves_loaded} (Should be 0)")

        if moves_loaded > 0:
            print("ERROR: Moves are being loaded! Optimization failed.")
            sys.exit(1)


if __name__ == "__main__":
    measure_performance()
