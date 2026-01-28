import { useState, useCallback, useEffect, useMemo } from 'react';
import { Chess, Square, PieceSymbol, Color } from 'chess.js';
import {
  analyzeIllegalMove,
  IllegalMoveAnalysis,
  ARROW_COLOR_RED,
  ARROW_COLOR_GREEN,
} from '../lib/chess-logic';
import { MoveRecordResponse } from '../api/types';

// Shared type (could be moved to types.ts)
export type Arrow = {
  startSquare: string;
  endSquare: string;
  color: string;
  borderColor?: string;
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
  const startFen = useMemo(() => {
    const c = new Chess();
    if (initialFen) c.load(initialFen);
    else c.reset();
    return c.fen();
  }, [initialFen]);

  // Pre-calculate FEN history for O(1) access
  const fenCache = useMemo(() => {
    const cache: string[] = [];
    const tempChess = new Chess();
    if (initialFen) tempChess.load(initialFen);
    else tempChess.reset();

    gameMoves.forEach((move) => {
      if (move && !move.is_illegal && move.actual_move) {
        try {
          tempChess.move(move.actual_move);
        } catch {
          // Ignore invalid moves in history
        }
      }
      cache.push(tempChess.fen());
    });
    return cache;
  }, [gameMoves, initialFen]);

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

      // Get state BEFORE the move at index
      const currentFen = index > 0 ? fenCache[index - 1] : startFen;
      const tempChess = new Chess(currentFen);
      const currentTurn = tempChess.turn();
      const arrowBorderColor = currentTurn === 'w' ? 'white' : 'black';

      // 1. Expected Move Arrow (Green)
      if (moveRecord.expected_move) {
        const expectedState = new Chess(currentFen);
        try {
          const result = expectedState.move(moveRecord.expected_move);
          if (result) {
            newArrows.push({
              startSquare: result.from,
              endSquare: result.to,
              color: ARROW_COLOR_GREEN,
              borderColor: arrowBorderColor,
            });
          }
        } catch {
          // Expected move might be invalid in current state if something is wrong
        }
      }

      // 2. Actual/Illegal Move Arrow (Red)
      if (moveRecord.actual_move && moveRecord.actual_move !== moveRecord.expected_move) {
        // Illegal move - get analyzed source/target
        const analysis = analyzeIllegalMove(currentFen, moveRecord.actual_move, agentColor);
        if (analysis.targetSquare) {
          if (analysis.sourceSquare) {
            newArrows.push({
              startSquare: analysis.sourceSquare,
              endSquare: analysis.targetSquare,
              color: ARROW_COLOR_RED, // Red color
              borderColor: arrowBorderColor,
            });
          }
          newCustomSquares[analysis.targetSquare] = {
            background: 'rgba(255, 0, 0, 0.4)',
          };
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
    [gameMoves, fenCache, startFen, hallucinatedSquare, agentColor]
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
        setBoardPosition(startFen);
        setCurrentMoveIndex(-1);
        setArrows([]);
        setCustomSquareStyles({});
        return;
      }

      const moveRecord = gameMoves[index];

      // Get state BEFORE the move at index
      const baseFen = index > 0 ? fenCache[index - 1] : startFen;

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

          // Determine intended piece attributes for visualization
          let movePieceColor = agentColor === 'white' ? 'w' : 'b';
          let movePieceType = analysis.pieceType as PieceSymbol;

          if (analysis.sourceSquare) {
            const pieceAtSource = checkState.get(analysis.sourceSquare as Square);
            if (pieceAtSource) {
              // Match the actual piece that was moved (handle ownership hallucination)
              movePieceColor = pieceAtSource.color;
              movePieceType = pieceAtSource.type;

              // Only remove from source if it belongs to the agent
              // (If moving opponent piece, keep the original piece visible)
              if (pieceAtSource.color === (agentColor === 'white' ? 'w' : 'b')) {
                checkState.remove(analysis.sourceSquare as Square);
              }
            }
          }

          if (movePieceType) {
            checkState.put(
              { type: movePieceType, color: movePieceColor as Color },
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
          setBoardPosition(fenCache[index]);
        }
      }

      setCurrentMoveIndex(index);
    },
    [gameMoves, fenCache, startFen, agentColor]
  );

  // Initialize board on load
  useEffect(() => {
    setBoardPosition(startFen);
    setCurrentMoveIndex(-1);
  }, [startFen]);

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
