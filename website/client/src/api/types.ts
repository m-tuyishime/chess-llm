export interface HealthResponse {
  status: string;
}

export interface PuzzleResponse {
  id: string;
  fen: string;
  moves: string;
  rating: number;
  rating_deviation: number;
  themes: string;
  type: string;
  popularity: number;
  nb_plays: number;
  game_url: string;
  opening_tags: string;
}

export interface MoveRecordResponse {
  fen: string;
  expected_move: string;
  actual_move: string;
  is_illegal: boolean;
  prompt_tokens: number;
  completion_tokens: number;
  game_id?: number | null;
  id?: number | null;
}

export interface GameResponse {
  id: number | null;
  puzzle_id: string;
  puzzle_type: string;
  agent_name: string;
  failed: boolean;
  moves: MoveRecordResponse[];
  date: string; // ISO 8601 string
}

export interface GameSummaryResponse {
  id: number | null;
  puzzle_id: string;
  puzzle_type: string;
  agent_name: string;
  failed: boolean;
  move_count: number;
  date: string;
}

export interface AgentRankingResponse {
  name: string;
  rating: number;
  rd: number;
  win_rate: number;
  games_played: number;
}

export interface AgentDetailResponse {
  name: string;
  is_reasoning: boolean;
  is_random: boolean;
  rating: number;
  rd: number;
  volatility: number;
  games: GameSummaryResponse[];
}

export interface BenchmarkDataResponse {
  agent_name: string;
  agent_rating: number;
  agent_deviation: number;
  agent_volatility: number;
  date: string;
  evaluation_index: number;
}

export interface PuzzleOutcomeResponse {
  type: string;
  successes: number;
  failures: number;
}

export interface AgentPuzzleOutcomeResponse {
  agent_name: string;
  type: string;
  successes: number;
  failures: number;
}

export interface IllegalMoveResponse {
  agent_name: string;
  total_moves: number;
  illegal_moves_count: number;
  illegal_percentage: number;
}

export interface TokenUsageResponse {
  agent_name: string;
  avg_prompt_tokens: number;
  avg_completion_tokens: number;
}

export interface AnalyticsResponse {
  rating_trends: BenchmarkDataResponse[];
  puzzle_outcomes: PuzzleOutcomeResponse[];
  illegal_moves: IllegalMoveResponse[];
  token_usage: TokenUsageResponse[];
}
