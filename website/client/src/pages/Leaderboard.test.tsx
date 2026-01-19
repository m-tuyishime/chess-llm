import { render, screen, waitFor } from '@testing-library/react';
import { Leaderboard } from './Leaderboard';
import { api } from '../api/client';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

// Mock the API client
vi.mock('../api/client', () => ({
  api: {
    getLeaderboard: vi.fn(),
  },
}));

const mockRankings = [
  {
    name: 'Agent-001',
    rating: 1500,
    rd: 30,
    win_rate: 0.55,
    games_played: 100,
  },
  {
    name: 'Stockfish-Level-1',
    rating: 1200,
    rd: 40,
    win_rate: 0.1,
    games_played: 20,
  },
];

describe('Leaderboard Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', () => {
    // Return a promise that doesn't resolve immediately to test loading state
    vi.mocked(api.getLeaderboard).mockReturnValue(new Promise(() => {}));
    render(
      <MemoryRouter>
        <Leaderboard />
      </MemoryRouter>
    );
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('renders leaderboard data after fetch', async () => {
    vi.mocked(api.getLeaderboard).mockResolvedValue(mockRankings);
    render(
      <MemoryRouter>
        <Leaderboard />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.queryByText(/loading/i)).not.toBeInTheDocument();
    });

    expect(screen.getByText('Agent-001')).toBeInTheDocument();
    expect(screen.getByText('1500')).toBeInTheDocument();
    expect(screen.getByText('Stockfish-Level-1')).toBeInTheDocument();
    expect(screen.getByText('55.0%')).toBeInTheDocument(); // Assuming formatting
  });

  it('renders error state on API failure', async () => {
    vi.mocked(api.getLeaderboard).mockRejectedValue(new Error('Failed to fetch'));
    render(
      <MemoryRouter>
        <Leaderboard />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });
  });
});
