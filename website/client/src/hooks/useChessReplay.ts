import { useState, useCallback, useEffect } from 'react';
import { Chess, Square, PieceSymbol, Color } from 'chess.js';
import { analyzeIllegalMove, IllegalMoveAnalysis } from '../lib/chess-logic';
import { MoveRecordResponse } from '../api/types';

// Shared type (could be moved to types.ts)
export type Arrow = {
  startSquare: string;
  endSquare: string;
  color: string;
};

/**
 * Props for the useChessReplay hook.
 */
interface UseChessReplayProps {
  initialFen?: string;
  gameMoves: MoveRecordResponse[];
  agentColor: 'white' | 'black';
}

/**
 * Hook to manage chess replay logic, including illegal move visualization.
 * @param props - The hook props.
 * @param props.initialFen - The starting FEN position.
 * @param props.gameMoves - The list of moves in the game.
 * @param props.agentColor - The color the agent is playing as.
 * @returns The replay state and controls.
 */
export function useChessReplay({ initialFen, gameMoves, agentColor }: UseChessReplayProps) {
  // Core State
  const [chess] = useState(new Chess());
  const [currentMoveIndex, setCurrentMoveIndex] = useState(-1);
  const [boardPosition, setBoardPosition] = useState('');
  const [arrows, setArrows] = useState<Arrow[]>([]);
  const [customSquareStyles, setCustomSquareStyles] = useState<Record<string, React.CSSProperties>>(
    {}
  );

  // Illegal/Hallucination State
  const [hallucinatedSquare, setHallucinatedSquare] = useState<string | null>(null);
  const [illegalSquare, setIllegalSquare] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<IllegalMoveAnalysis | null>(null);

  // Computed Initial State
  const getBaseChess = useCallback(() => {
    const c = new Chess();
    if (initialFen) c.load(initialFen);
    else c.reset();
    return c;
  }, [initialFen]);

  // Update Arrows & Styles Logic
  const updateVisuals = useCallback(
    (index: number) => {
      const moveRecord = gameMoves[index];
      if (!moveRecord) {
        setArrows([]);
        setCustomSquareStyles({});
        return;
      }

      const newArrows: Arrow[] = [];
      const newCustomSquares: Record<string, React.CSSProperties> = {};

      // Replay to current state
      const tempChess = getBaseChess();
      for (let i = 0; i < index; i++) {
        const m = gameMoves[i];
        if (m && !m.is_illegal && m.actual_move) {
          try {
            tempChess.move(m.actual_move);
          } catch {
            // Ignore invalid moves in history during fast replay
          }
        }
      }
      const currentFen = tempChess.fen();

      // 1. Expected Move Arrow (Green)
      if (moveRecord.expected_move) {
        const expectedState = new Chess(currentFen);
        try {
          const result = expectedState.move(moveRecord.expected_move);
          if (result) {
            newArrows.push({
              startSquare: result.from,
              endSquare: result.to,
              color: 'rgba(34, 197, 94, 0.9)',
            });
          }
        } catch {
          // Expected move might be invalid in current state if something is wrong
        }
      }

      // 2. Actual/Illegal Move Arrow (Red)
      if (moveRecord.actual_move && moveRecord.actual_move !== moveRecord.expected_move) {
        const actualState = new Chess(currentFen);
        try {
          const result = actualState.move(moveRecord.actual_move);
          if (result) {
            newArrows.push({
              startSquare: result.from,
              endSquare: result.to,
              color: 'rgba(239, 68, 68, 0.9)',
            });
          }
        } catch {
          // Illegal move - try to get analyzed source/target
          const analysis = analyzeIllegalMove(currentFen, moveRecord.actual_move, agentColor);
          if (analysis.targetSquare) {
            if (analysis.sourceSquare) {
              newArrows.push({
                startSquare: analysis.sourceSquare,
                endSquare: analysis.targetSquare,
                color: 'rgba(239, 68, 68, 0.9)', // Red color
              });
            }
            newCustomSquares[analysis.targetSquare] = {
              background: 'rgba(255, 0, 0, 0.4)',
            };
          }
        }
      }

      setArrows(newArrows);

      // Apply hallucination red background if needed
      if (hallucinatedSquare) {
        newCustomSquares[hallucinatedSquare] = {
          ...newCustomSquares[hallucinatedSquare],
          background: 'rgba(255, 0, 0, 0.4)',
        };
      }

      setCustomSquareStyles(newCustomSquares);
    },
    [gameMoves, getBaseChess, hallucinatedSquare, agentColor]
  );

  // Sync visuals when special states change
  useEffect(() => {
    updateVisuals(currentMoveIndex);
  }, [hallucinatedSquare, illegalSquare, updateVisuals, currentMoveIndex]);

  const goToMove = useCallback(
    (index: number) => {
      // Reset special states when maneuvering
      setHallucinatedSquare(null);
      setIllegalSquare(null);
      setAnalysisResult(null);

      if (index === -1) {
        const base = getBaseChess();
        setBoardPosition(base.fen());
        setCurrentMoveIndex(-1);
        setArrows([]);
        setCustomSquareStyles({});
        return;
      }

      const moveRecord = gameMoves[index];
      const tempChess = getBaseChess();

      // Replay moves up to index
      for (let i = 0; i < index; i++) {
        const m = gameMoves[i];
        if (m && !m.is_illegal && m.actual_move) {
          try {
            tempChess.move(m.actual_move);
          } catch {
            // Ignore
          }
        }
      }
      const baseFen = tempChess.fen(); // FEN before the current move

      if (moveRecord?.is_illegal) {
        // Handle Illegal State
        const analysis = analyzeIllegalMove(baseFen, moveRecord.actual_move, agentColor);
        setAnalysisResult(analysis);

        let displayFen = baseFen;

        if (analysis.type === 'hallucination') {
          setHallucinatedSquare(analysis.targetSquare);
        }

        if (analysis.targetSquare) {
          setIllegalSquare(analysis.targetSquare);

          // Prepare the visualized board
          const checkState = new Chess(baseFen);
          if (analysis.sourceSquare) {
            checkState.remove(analysis.sourceSquare as Square);
          }

          const turnColor = agentColor === 'white' ? 'w' : 'b';
          if (analysis.pieceType) {
            checkState.put(
              { type: analysis.pieceType as PieceSymbol, color: turnColor as Color },
              analysis.targetSquare as Square
            );
          }
          displayFen = checkState.fen();
        }

        setBoardPosition(displayFen);
      } else {
        // Valid move
        if (moveRecord && moveRecord.fen) {
          setBoardPosition(moveRecord.fen);
        } else {
          // Fallback simulation
          try {
            tempChess.move(moveRecord.actual_move);
          } catch {
            // Fallback move failed
          }
          setBoardPosition(tempChess.fen());
        }
      }

      setCurrentMoveIndex(index);
    },
    [gameMoves, getBaseChess, agentColor]
  );

  // Initialize board on load
  useEffect(() => {
    const base = getBaseChess();
    setBoardPosition(base.fen());
    setCurrentMoveIndex(-1);
  }, [getBaseChess]);

  return {
    chess,
    currentMoveIndex,
    boardPosition,
    arrows,
    customSquareStyles,
    hallucinatedSquare,
    illegalSquare,
    analysisResult,
    goToMove,
  };
}
