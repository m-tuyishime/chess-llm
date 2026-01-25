// React import removed (unused)
// Icons removed (unused)

import { MoveRecordResponse } from '../api/types';

/**
 * Props for the MoveHistory component.
 */
interface MoveHistoryProps {
  /** List of move records to display */
  moves: MoveRecordResponse[];
  /** Index of the currently selected move */
  currentMoveIndex: number;
  /** Callback to navigate to a specific move index */
  goToMove: (index: number) => void;
}

/**
 * Component to display the history of moves in a game.
 * @param props - The component props.
 * @param props.moves - List of move records to display.
 * @param props.currentMoveIndex - Index of the currently selected move.
 * @param props.goToMove - Callback to navigate to a specific move index.
 * @returns The rendered component.
 */
export function MoveHistory({ moves, currentMoveIndex, goToMove }: MoveHistoryProps) {
  const rowCount = Math.ceil((moves.length || 0) / 2);

  return (
    <div className="move-history-container">
      <div
        className="sidebar-section-header has-tooltip"
        style={{ background: 'var(--bg-app)' }}
        data-tooltip="A complete chronological history of every move played in this game."
      >
        Move Records
      </div>
      <div className="replay-sidebar-content custom-scrollbar">
        <table className="move-history-table">
          <thead>
            <tr>
              <th className="th-number">#</th>
              <th className="th-move">White</th>
              <th className="th-move">Black</th>
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: rowCount }).map((_, i) => {
              const whiteMoveIndex = i * 2;
              const blackMoveIndex = i * 2 + 1;
              const whiteMove = moves[whiteMoveIndex];
              const blackMove = moves[blackMoveIndex];
              const isCurrentRow = Math.floor(currentMoveIndex / 2) === i;

              return (
                <tr key={i} className={isCurrentRow ? 'current-row' : ''}>
                  <td className="td-number">{i + 1}.</td>

                  {/* White Move */}
                  <td
                    onClick={() => whiteMove && goToMove(whiteMoveIndex)}
                    className={`history-cell ${currentMoveIndex === whiteMoveIndex ? 'active' : ''} ${whiteMove?.is_illegal ? 'illegal' : ''}`}
                    style={{ cursor: whiteMove ? 'pointer' : 'default' }}
                  >
                    {whiteMove ? whiteMove.actual_move : ''}
                    {whiteMove?.is_illegal && <span className="illegal-tag">(Illegal)</span>}
                  </td>

                  {/* Black Move */}
                  <td
                    onClick={() => blackMove && goToMove(blackMoveIndex)}
                    className={`history-cell ${currentMoveIndex === blackMoveIndex ? 'active' : ''} ${blackMove?.is_illegal ? 'illegal' : ''}`}
                    style={{ cursor: blackMove ? 'pointer' : 'default' }}
                  >
                    {blackMove ? blackMove.actual_move : ''}
                    {blackMove?.is_illegal && <span className="illegal-tag">(Illegal)</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
