import { renderHook, act } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { useChessReplay } from './useChessReplay';
import { MoveRecordResponse } from '../api/types';

describe('useChessReplay', () => {
  const mockMoves = [
    {
      actual_move: 'e4',
      expected_move: 'e4',
      fen: 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1',
    },
    {
      actual_move: 'e5',
      expected_move: 'e5',
      fen: 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/AAAA1PPP/RNBQKBNR w KQkq - 0 2',
    },
  ];

  it('initializes correctly', () => {
    const { result } = renderHook(() =>
      useChessReplay({
        gameMoves: mockMoves as unknown as MoveRecordResponse[],
        agentColor: 'white',
      })
    );

    expect(result.current.currentMoveIndex).toBe(-1);
    expect(result.current.boardPosition).toBe(
      'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
    ); // Start pos
  });

  it('navigates to next move', () => {
    const { result } = renderHook(() =>
      useChessReplay({
        gameMoves: mockMoves as unknown as MoveRecordResponse[],
        agentColor: 'white',
      })
    );

    act(() => {
      result.current.goToMove(0);
    });

    expect(result.current.currentMoveIndex).toBe(0);
    expect(result.current.boardPosition).toBe(mockMoves[0].fen);
  });

  it('handles illegal move (hallucination)', () => {
    // Setup: Board with NO Queen for white
    const noQueenFen = '4k3/4p3/8/8/8/8/4P3/4K3 w - - 0 1';

    const illegalMoves = [{ actual_move: 'Qc6', expected_move: 'e4', is_illegal: true }];

    const { result } = renderHook(() =>
      useChessReplay({
        initialFen: noQueenFen,
        gameMoves: illegalMoves as unknown as MoveRecordResponse[],
        agentColor: 'white',
      })
    );

    act(() => {
      result.current.goToMove(0);
    });

    expect(result.current.currentMoveIndex).toBe(0);
    // Should detect hallucination
    expect(result.current.hallucinatedSquare).toBe('c6'); // Target of Qc6
    expect(result.current.illegalSquare).toBe('c6');
  });

  it('resets illegal state when maneuvering', () => {
    // Setup: Board with NO Queen for white
    const noQueenFen = '4k3/4p3/8/8/8/8/4P3/4K3 w - - 0 1';
    const illegalMoves = [{ actual_move: 'Qc6', expected_move: 'e4', is_illegal: true }];
    const { result } = renderHook(() =>
      useChessReplay({
        initialFen: noQueenFen,
        gameMoves: illegalMoves as unknown as MoveRecordResponse[],
        agentColor: 'white',
      })
    );

    // Go to illegal
    act(() => result.current.goToMove(0));
    expect(result.current.hallucinatedSquare).toBe('c6');

    // Go back
    act(() => result.current.goToMove(-1));
    expect(result.current.hallucinatedSquare).toBeNull();
    expect(result.current.illegalSquare).toBeNull();
  });
});
