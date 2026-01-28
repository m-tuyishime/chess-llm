import json
import sqlite3
from pathlib import Path


def export_puzzles() -> None:
    db_path = Path("data/storage.db")
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM puzzle")
        rows = cursor.fetchall()

        puzzles = [dict(row) for row in rows]

        output_path = Path("data/puzzles.json")
        with open(output_path, "w") as f:
            json.dump(puzzles, f, indent=2)

        print(f"Exported {len(puzzles)} puzzles to {output_path}")

    except Exception as e:
        print(f"Error exporting puzzles: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    export_puzzles()
