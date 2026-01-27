import { render, screen, waitFor } from '@testing-library/react';
import { AgentDetail } from './AgentDetail';
import { api } from '../api/client';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

// Mock the API client
vi.mock('../api/client', () => ({
  api: {
    getAgentDetail: vi.fn(),
  },
}));

const mockAgentDetail = {
  name: 'Agent-001',
  is_reasoning: false,
  is_random: false,
  rating: 1500,
  rd: 30,
  volatility: 0.06,
  games: Array.from({ length: 25 }, (_, i) => ({
    id: i + 1,
    puzzle_id: `puzzle-${i}`,
    puzzle_type: i % 2 === 0 ? 'MateIn2' : 'Opening',
    agent_name: 'Agent-001',
    failed: i % 3 === 0, // Some failed, some success (failed=false means success)
    move_count: 5,
    date: new Date().toISOString(),
  })),
};

describe('AgentDetail Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderComponent = (name = 'Agent-001') => {
    return render(
      <MemoryRouter initialEntries={[`/agent/${name}`]}>
        <Routes>
          <Route path="/agent/:name" element={<AgentDetail />} />
        </Routes>
      </MemoryRouter>
    );
  };

  it('renders loading state initially', () => {
    vi.mocked(api.getAgentDetail).mockReturnValue(new Promise(() => {}));
    renderComponent();
    // Use accessible name or sr-only text
    expect(screen.getByText(/loading agent details/i)).toBeInTheDocument();
  });

  it('renders error state on API failure', async () => {
    vi.mocked(api.getAgentDetail).mockRejectedValue(new Error('Failed to fetch'));
    renderComponent();
    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });
  });

  it('renders agent stats and games table after fetch', async () => {
    vi.mocked(api.getAgentDetail).mockResolvedValue(mockAgentDetail);
    renderComponent();

    await waitFor(() => {
      expect(screen.queryByText(/loading agent details/i)).not.toBeInTheDocument();
    });

    expect(screen.getByText('Agent-001')).toBeInTheDocument();
    // Use getAllByText if it appears multiple times or use more specific query
    const ratingElements = screen.getAllByText('1500');
    expect(ratingElements.length).toBeGreaterThan(0);

    expect(screen.getByText('Game History')).toBeInTheDocument();
  });

  it('paginates games list', async () => {
    vi.mocked(api.getAgentDetail).mockResolvedValue(mockAgentDetail);
    renderComponent();
    await waitFor(() => expect(screen.queryByText(/loading/i)).not.toBeInTheDocument());

    // Mock has 25 games, page size is 15. Expect 2 pages.
    // UI shows "Showing 1 - 15 of 25"
    expect(screen.getByText(/Showing 1 - 15 of 25/i)).toBeInTheDocument();

    // Check for "Next" button
    const nextButton = screen.getByRole('button', { name: /next/i });
    expect(nextButton).toBeInTheDocument();
    expect(nextButton).not.toBeDisabled();
  });
});
