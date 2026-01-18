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
  agent_name: string;
  failed: boolean;
  moves: MoveRecordResponse[];
  date: string; // ISO 8601 string
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
  games: GameResponse[];
}
