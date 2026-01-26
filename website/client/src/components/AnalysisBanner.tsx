import { parseMove } from '../lib/chess-logic';

interface MoveRecord {
  is_illegal?: boolean;
  expected_move?: string;
  actual_move?: string;
}

/**
 * Props for the AnalysisBanner component.
 */
interface AnalysisBannerProps {
  /** The current move record being displayed */
  currentMove: MoveRecord | null | undefined;
  /** The square where a piece was hallucinated, if any */
  hallucinatedSquare: string | null;
  /** The target square of an illegal move, if any */
  illegalSquare: string | null;
  /** Detailed analysis message from the hook */
  analysisMessage?: string | null;
}

/**
 * Component to display analysis feedback for a move (illegal, incorrect, etc.).
 * @param props - The component props.
 * @param props.currentMove - The current move record being displayed.
 * @param props.hallucinatedSquare - The square where a piece was hallucinated, if any.
 * @param props.illegalSquare - The target square of an illegal move, if any.
 * @param props.analysisMessage - Detailed analysis message from the hook.
 * @returns The rendered banner or null.
 */
export function AnalysisBanner({
  currentMove,
  hallucinatedSquare,
  illegalSquare,
  analysisMessage,
}: AnalysisBannerProps) {
  if (!currentMove) return null;

  const isIllegal = currentMove.is_illegal;
  const isIncorrect =
    currentMove.expected_move && currentMove.actual_move !== currentMove.expected_move;

  if (!isIllegal && !isIncorrect) return null;

  // Parse move details for better messages
  const parsed = parseMove(currentMove.actual_move || '');
  const pieceType = parsed ? parsed.pieceType.toUpperCase() : 'Piece';
  const targetSq = parsed ? parsed.targetSquare : '?';
  const actualMove = currentMove.actual_move || '?';

  let message = analysisMessage || '';

  if (!message) {
    if (isIllegal) {
      if (hallucinatedSquare) {
        message = `The agent tried to move a non-existent ${pieceType} to ${targetSq} (Hallucination).`;
      } else if (illegalSquare) {
        message = `The agent tried to move ${pieceType} to ${targetSq}, but it was an illegal move.`;
      } else {
        message = `The agent selected an illegal move (${actualMove}).`;
      }
    } else {
      message = `The agent played ${actualMove}, but the optimal move was ${currentMove.expected_move}.`;
    }
  }

  const title = analysisMessage?.includes('unusual')
    ? 'Unusual Notation'
    : isIllegal
      ? 'Illegal Move'
      : 'Incorrect Move';

  return (
    <div className="analysis-banner-wrapper">
      <div className="analysis-banner-title">{title}</div>
      <div className="analysis-banner-message">{message}</div>
    </div>
  );
}
