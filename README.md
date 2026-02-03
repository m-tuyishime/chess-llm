# LLM Chess Puzzle Performance Analysis

## Overview

This project presents a comparative analysis of the performance of various Large Language Models (LLMs) in solving chess puzzles. An automated evaluation system was developed using Python to benchmark different LLMs against a diverse set of chess puzzles sourced from the Lichess database, categorized by themes like "End Game", "Strategic", and "Tactic". The system employs the Glicko-2 rating system to estimate and compare the playing strength of the models in a manner comparable to human chess ratings.

The primary goal was to systematically evaluate LLM performance across varying puzzle difficulties and themes, identifying model strengths, weaknesses, and quantifying phenomena like hallucinations (generating illegal moves).

## Key Features & Highlights

- **Live Website:** Interactive web interface available at [chessllm.tuyishime.ca](https://chessllm.tuyishime.ca) for exploring leaderboards, agent performance, and game replays.
- **Glicko-2 Rating:** Utilizes the Glicko-2 rating system for statistically sound performance comparison and estimation of playing strength.
- **Modular Architecture:** Built with a modular design featuring distinct components for agents (LLM, Stockfish, Random), chess environment simulation (`ChessEnv`), evaluation orchestration (`Evaluator`), data management (`DatabaseManager`), puzzle selection (`PuzzleSelector`), API interaction (`Router`), and report generation (`ReportGenerator`).
- **Asynchronous Processing:** Leverages Python's `asyncio` for efficient parallel evaluation of multiple LLMs and handling of API calls.
- **API Management:** Includes components for managing API keys, routing requests to different providers (e.g., OpenRouter, Nvidia NIM), and handling rate limits (`AsyncLimiter`).
- **Constraint Handling:** Demonstrated adaptability by overcoming budget limitations and API restrictions through strategic selection of models and platforms (e.g., shifting to Nvidia NIM for free access to open-source models).
- **Data Storage:** Employs SQLite for efficient data storage and retrieval, with a schema designed to accommodate various evaluation metrics and results.

## Exploring Results

Visit the live website at **[chessllm.tuyishime.ca](https://chessllm.tuyishime.ca)** to:

- View the **Leaderboard** of LLM chess agents ranked by Glicko-2 rating
- Explore detailed **Agent Performance** breakdowns by puzzle type
- Watch **Game Replays** with move-by-move analysis
- Analyze **Performance Trends** and rating evolution

## Setup Instructions

1.  **Prerequisites:**
    - Python 3.11+
    - [uv](https://docs.astral.sh/uv/) package manager
2.  **Clone Repository:**
    ```bash
    git clone <your-repository-url>
    cd <repository-directory>
    ```
3.  **Install Dependencies:**
    ```bash
    uv sync
    ```
4.  **Configure Environment Variables:**
    - Copy `.env.example` to `.env`:
      ```bash
      cp .env.example .env
      ```
    - Edit `.env` and provide your API keys for `OPENROUTER_API_KEY` or `NIM_API_KEY`.
    - Ensure `STOCKFISH_PATH` points to your Stockfish executable and `DB_PATH` points to the desired database location (default is `data/storage.db`).

## Running the Evaluation

- The evaluation script is located at `examples/scripts/run_evaluation.py`.
- Execute it using `uv`:
  ```bash
  uv run python examples/scripts/run_evaluation.py
  ```
- The script will:
  - Initialize agents (LLMs, Stockfish, Random).
  - Select puzzles for each agent that haven't been completed yet.
  - Run evaluations concurrently using `asyncio`.
  - Handle API rate limits.
  - Record game details, moves (including illegal ones), token counts, and Glicko-2 rating updates to the SQLite database (`data/storage.db`).
  - Log progress and errors.
- You can customize the script to evaluate different models or adjust evaluation parameters.

## Generating Reports

- After running evaluations, use the `reports.ipynb` Jupyter notebook to analyze the results stored in the database.
- This notebook uses the `ReportGenerator` module to create various visualizations, including:
  - Rating and rating deviation trends over time.
  - Success/failure rates by puzzle type and agent.
  - Distribution of illegal moves.
  - Final ratings with confidence intervals.
  - Success rates based on puzzle difficulty.

## Key Findings (As of April 2025)

- The evaluated LLMs generally performed below an average human chess player rating (approx. 1500 Glicko-2) on puzzle-solving tasks.
- The highest-rated LLM achieved a Glicko-2 rating of approximately 705 ± 81.
- LLMs exhibited limitations in adhering to formal game rules, frequently generating illegal moves ("hallucinations").

For visualization of the results, refer to the `reports.ipynb` Jupyter notebook.
