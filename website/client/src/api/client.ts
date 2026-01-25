import {
  AgentDetailResponse,
  AgentRankingResponse,
  GameResponse,
  HealthResponse,
  PuzzleResponse,
} from './types';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * Generic Fetch wrapper handling errors and typing.
 * @param endpoint The API endpoint (e.g. /api/health)
 * @param options Fetch options
 * @returns Promise with typed response
 */
async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(response.status, errorBody.detail || response.statusText);
  }

  return response.json();
}

export const api = {
  getHealth: () => request<HealthResponse>('/health'),
  getLeaderboard: () => request<AgentRankingResponse[]>('/api/leaderboard'),
  getAgentDetail: (name: string) =>
    request<AgentDetailResponse>(`/api/agents/${encodeURIComponent(name)}`),
  getGame: (id: string) => request<GameResponse>(`/api/games/${id}`),
  getPuzzle: (id: string) => request<PuzzleResponse>(`/api/puzzles/${id}`),
};
