import { useTranslation } from 'react-i18next';
import { MoveRecordResponse } from '../api/types';
import { parseMove, IllegalMoveAnalysis } from '../lib/chess-logic';

/**
 * Props for the AnalysisBanner component.
 */
interface AnalysisBannerProps {
  /** The current move record being displayed */
  currentMove: MoveRecordResponse | null | undefined;
  /** The square where a piece was hallucinated, if any */
  hallucinatedSquare: string | null;
  /** The target square of an illegal move, if any */
  illegalSquare: string | null;
  /** Detailed analysis of an illegal move */
  analysisResult?: IllegalMoveAnalysis;
}

/**
 * Component to display analysis feedback for a move (illegal, incorrect, etc.).
 * @param props - The component props.
 * @param props.currentMove - The current move record being displayed.
 * @param props.hallucinatedSquare - The square where a piece was hallucinated, if any.
 * @param props.illegalSquare - The target square of an illegal move, if any.
 * @param props.analysisResult - Detailed analysis of an illegal move.
 * @returns The rendered banner or null.
 */
export function AnalysisBanner({
  currentMove,
  hallucinatedSquare,
  illegalSquare,
  analysisResult,
}: AnalysisBannerProps) {
  const { t } = useTranslation();
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

  let message = '';

  if (isIllegal) {
    if (analysisResult?.description) {
      message = analysisResult.description;
    } else if (hallucinatedSquare) {
      message = t('replay.messages.hallucination', { piece: pieceType, target: targetSq });
    } else if (illegalSquare) {
      message = t('replay.messages.illegal', { piece: pieceType, target: targetSq });
    } else {
      message = t('replay.messages.genericIllegal', { move: actualMove });
    }
  } else {
    message = t('replay.messages.incorrect', {
      move: actualMove,
      expected: currentMove.expected_move,
    });
  }

  return (
    <div className="analysis-banner-wrapper">
      <div className="analysis-banner-title">
        {isIllegal
          ? analysisResult?.type === 'legal'
            ? t('replay.messages.notationError')
            : t('replay.messages.illegalMove')
          : t('replay.messages.incorrectMove')}
      </div>
      <div className="analysis-banner-message">{message}</div>
    </div>
  );
}
