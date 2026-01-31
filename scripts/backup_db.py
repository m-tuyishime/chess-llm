import argparse
import logging

from chess_llm_eval.data.backup import FullDatabaseBackup

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("backup_db")


def run_backup(json_path: str | None = None, dump_path: str | None = None) -> None:
    backup = FullDatabaseBackup("data/storage.db")

    logger.info("Starting Full Database Backup...")

    # JSON Backup
    final_json = backup.export_all_to_json(json_path)
    logger.info(f"JSON Backup successful: {final_json}")

    # SQLite Dump
    final_dump = backup.sqlite_dump(dump_path)
    logger.info(f"SQLite Dump successful: {final_dump}")

    # Simple verification
    import os

    json_size = os.path.getsize(final_json) / 1024 / 1024
    dump_size = os.path.getsize(final_dump) / 1024 / 1024
    logger.info(f"Stats: JSON ({json_size:.2f} MB), Dump ({dump_size:.2f} MB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backup the Chess-LLM Arena database.")
    parser.add_argument("--json", help="Path to save JSON backup")
    parser.add_argument("--dump", help="Path to save SQL dump")

    args = parser.parse_args()
    run_backup(args.json, args.dump)
