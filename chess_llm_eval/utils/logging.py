import logging
import os
from datetime import datetime


def setup_logging(log_level: int = logging.INFO) -> logging.Logger:
    """
    Configure logging for the chess-llm evaluation library.
    Creates a 'logs' directory and adds both file and stream handlers.
    """
    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"chess_eval_{timestamp}.log")

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )

    # Mute noisy loggers
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.INFO)

    return logging.getLogger("chess_llm_eval")
