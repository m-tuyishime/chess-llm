import { render, screen, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { ReplayPage } from './ReplayPage';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import * as api from '../api/client';

// Mock react-chessboard to inspect props
vi.mock('react-chessboard', () => ({
  Chessboard: ({ options }: { options: { position?: string; squareStyles?: unknown } }) => {
    return (
      <div data-testid="chessboard">
        <span data-testid="board-position">{options?.position}</span>
        <span data-testid="board-styles">{JSON.stringify(options?.squareStyles)}</span>
      </div>
    );
  },
}));

// Mock API
const mockGame = {
  id: 10250,
  agent_name: 'test-agent',
  white_agent_name: 'test-agent',
  black_agent_name: 'stockfish',
  result: '0-1',
  date: '2025-04-21T00:00:00',
  puzzle_id: 'test-puzzle',
  puzzle_type: 'mateIn2',
  moves: [
    {
      actual_move: 'Qg1',
      expected_move: 'Qg1',
      fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPP2QQ/RNBXKBNR w KQkq - 1 1',
      is_illegal: false,
      prompt_tokens: 10,
      completion_tokens: 5,
    }, // Fake Valid Move
    {
      actual_move: 'Qc6',
      expected_move: 'Rh1',
      fen: '',
      is_illegal: true,
      prompt_tokens: 0,
      completion_tokens: 0,
    }, // Illegal Move
  ],
  failed: true,
};

describe('ReplayPage Animation Logic', () => {
  beforeEach(() => {
    vi.spyOn(api.api, 'getGame').mockResolvedValue(mockGame);
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it('updates board position to illegal state transiently', async () => {
    // Initial Puzzle FEN (Approximate for test)
    // Let's assume start char is 'r'.

    render(
      <MemoryRouter initialEntries={['/replay/10250']}>
        <Routes>
          <Route path="/replay/:gameId" element={<ReplayPage />} />
        </Routes>
      </MemoryRouter>
    );

    // Wait for load
    await waitFor(() => expect(screen.getByTestId('chessboard')).not.toBeNull());

    // Click on Illegal Move (Row 2, index 1)
    // Text: "Qc6 (Illegal)"
    const moveRows = await screen.findAllByRole('row');
    const illegalRow = moveRows[2]; // Header + Move 1 + Move 2

    // Use act for click + state update
    await act(async () => {
      illegalRow.click(); // This might need finding the cell, but row click should fail? No, cell click.
      // Let's find by text
      const cell = screen.getByText(/Qc6/);
      cell.click();
    });

    // Check Board Position.
    // It should NOT be the valid FEN. It should be the manipulated FEN.
    // Valid FEN (Start) has piece at g1 (from move 1).
    // Illegal FEN should have piece at c6.

    const positionEl = screen.getByTestId('board-position');
    const initialPos = positionEl.textContent;
    console.log('Detected Position 1:', initialPos);

    expect(initialPos).toContain('c6'); // Not reliable text, FEN string.
    // FEN structure: r.../../..Q.
    // We expect the FEN string to change from "Safe" to "Illegal".

    // Ideally we check specific FEN content, but exact string is hard.
    // Just asserting it CHANGED is good first step.
    // And asserting it REVERTS.

    // Advance timer 1s
    await act(async () => {
      vi.advanceTimersByTime(1000);
    });

    const revertedPos = positionEl.textContent;
    console.log('Detected Position 2 (Reverted):', revertedPos);

    expect(revertedPos).not.toBe(initialPos);
    // Actually, revert means it goes back to "Base".
    // "InitialPos" captured above was "Illegal".
    // So Reverted != Illegal.
  });
});
