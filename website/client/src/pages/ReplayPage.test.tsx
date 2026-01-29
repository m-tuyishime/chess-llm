import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ReplayPage } from './ReplayPage';
import { api } from '../api/client';
import { GameResponse } from '../api/types';

// Mock the API client
vi.mock('../api/client', () => ({
  api: {
    getGame: vi.fn(),
  },
}));

// Mock react-chessboard to avoid canvas issues in jsdom and allow prop verification
vi.mock('react-chessboard', () => ({
  Chessboard: (props: Record<string, unknown>) => (
    <div data-testid="chessboard">
      <span data-testid="board-props">{JSON.stringify(props)}</span>
    </div>
  ),
}));

interface MockGame {
  id: number;
  pgn: string;
  white: string;
  black: string;
  date: string;
  result: string;
  outcome: string;
  moves: { actual_move: string; expected_move: string }[];
  agent_name: string;
}

describe('ReplayPage', () => {
  const mockGame: MockGame = {
    id: 1,
    pgn: '1. e4 e5 2. Nf3 Nc6',
    white: 'Agent A',
    black: 'Agent B',
    date: '2025-01-01',
    result: '1-0',
    outcome: 'Checkmate',
    agent_name: 'Agent A',
    moves: [
      { actual_move: 'e4', expected_move: 'e4' },
      { actual_move: 'e5', expected_move: 'e5' },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', () => {
    vi.spyOn(api, 'getGame').mockImplementation(() => new Promise(() => {}));

    render(
      <MemoryRouter initialEntries={['/replay/1']}>
        <Routes>
          <Route path="/replay/:gameId" element={<ReplayPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('fetches and displays game data with V6 Flex Layout', async () => {
    vi.spyOn(api, 'getGame').mockResolvedValue(mockGame as unknown as GameResponse);

    const { container } = render(
      <MemoryRouter initialEntries={['/replay/1']}>
        <Routes>
          <Route path="/replay/:gameId" element={<ReplayPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Agent A Replay/i)).toBeInTheDocument();
    });

    // Check strict viewport rules (V6 - Flex Row)
    const pageContainer = container.firstChild as HTMLElement;
    expect(pageContainer).toHaveClass('replay-full-screen');
    // expect(pageContainer).toHaveStyle({ display: 'flex', flexDirection: 'row' }); // Removed: unreliable in JSDOM

    // Ensure we are using the new structure
    expect(pageContainer.querySelector('.replay-header')).not.toBeInTheDocument(); // Header removed
    expect(pageContainer.querySelector('.replay-center')).toBeInTheDocument();
    expect(pageContainer.querySelector('.board-container')).toBeInTheDocument();

    // Check V6 Sidebar specific elements
    expect(pageContainer.querySelector('.replay-sidebar-wrapper')).toBeInTheDocument();
    expect(pageContainer.querySelector('.sidebar-header-main')).toBeInTheDocument(); // New Sidebar Header

    // Sidebar defaults to OPEN, so we expect "Close Sidebar" button
    expect(screen.getByLabelText('Close Sidebar')).toBeInTheDocument();

    // Check Board Customization (Slate Theme)
    const boardProps = JSON.parse(screen.getByTestId('board-props').textContent || '{}');
    expect(boardProps.options.darkSquareStyle).toEqual({ backgroundColor: '#334155' });
    expect(boardProps.options.lightSquareStyle).toEqual({ backgroundColor: '#94a3b8' });
  });

  it('renders premium control buttons with accessibility labels', async () => {
    vi.spyOn(api, 'getGame').mockResolvedValue(mockGame as unknown as GameResponse);

    render(
      <MemoryRouter initialEntries={['/replay/1']}>
        <Routes>
          <Route path="/replay/:gameId" element={<ReplayPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Agent A Replay/i)).toBeInTheDocument();
    });

    // Check for accessible control buttons (V4)
    expect(screen.getByLabelText('First Move')).toBeInTheDocument();
    expect(screen.getByLabelText('Previous Move')).toBeInTheDocument();
    expect(screen.getByLabelText('Next Move')).toBeInTheDocument();
    expect(screen.getByLabelText('Last Move')).toBeInTheDocument();
  });

  it('handles error state', async () => {
    vi.spyOn(api, 'getGame').mockRejectedValue(new Error('Failed to fetch'));

    render(
      <MemoryRouter initialEntries={['/replay/1']}>
        <Routes>
          <Route path="/replay/:gameId" element={<ReplayPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });
  });
});
