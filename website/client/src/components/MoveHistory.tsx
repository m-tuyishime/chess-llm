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
  /** The color of the side that makes the first move */
  startColor?: 'white' | 'black';
}

interface HistoryRow {
  number: number;
  white: { move: MoveRecordResponse; index: number } | null;
  black: { move: MoveRecordResponse; index: number } | null;
}

/**
 * Component to display the history of moves in a game.
 * @param props - The component props.
 * @param props.moves - List of move records to display.
 * @param props.currentMoveIndex - Index of the currently selected move.
 * @param props.goToMove - Callback to navigate to a specific move index.
 * @param props.startColor - The color of the side that makes the first move.
 * @returns The rendered component.
 */
export function MoveHistory({
  moves,
  currentMoveIndex,
  goToMove,
  startColor = 'white',
}: MoveHistoryProps) {
  // Group moves into rows handling retries and illegal moves
  const rows: HistoryRow[] = [];
  let currentNumber = 1;
  let currentRow: HistoryRow = { number: 1, white: null, black: null };
  let expectedColor = startColor;

  moves.forEach((move, index) => {
    if (expectedColor === 'white') {
      // If White slot is already taken (should theoretically happen if we didn't push, but our logic pushes)
      if (currentRow.white) {
        rows.push(currentRow);
        currentRow = { number: currentNumber, white: null, black: null };
      }

      currentRow.white = { move, index };

      if (!move.is_illegal) {
        expectedColor = 'black';
      } else {
        // Illegal: Retry means next move is also White.
        // Close this row so next White move gets a new line.
        rows.push(currentRow);
        currentRow = { number: currentNumber, white: null, black: null };
        // expectedColor stays 'white'
      }
    } else {
      // Expected Black
      // If Black slot is taken (unlikely unless logic error)
      if (currentRow.black) {
        rows.push(currentRow);
        currentRow = { number: currentNumber, white: null, black: null };
      }

      currentRow.black = { move, index };

      if (!move.is_illegal) {
        // Legal: Turn ends.
        rows.push(currentRow);
        currentNumber++;
        currentRow = { number: currentNumber, white: null, black: null };
        expectedColor = 'white';
      } else {
        // Illegal: Retry means next move is also Black.
        rows.push(currentRow);
        currentRow = { number: currentNumber, white: null, black: null };
        // expectedColor stays 'black'
      }
    }
  });

  // Push final partial row if exists
  if (currentRow.white || currentRow.black) {
    rows.push(currentRow);
  }

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
            {rows.map((row, i) => {
              const { white, black } = row;
              // Check if either move is the current one
              const isCurrentRow =
                (white && white.index === currentMoveIndex) ||
                (black && black.index === currentMoveIndex);

              return (
                <tr key={i} className={isCurrentRow ? 'current-row' : ''}>
                  <td className="td-number">{row.number}.</td>

                  {/* White Move */}
                  <td
                    onClick={() => white && goToMove(white.index)}
                    className={`history-cell ${white && currentMoveIndex === white.index ? 'active' : ''} ${white?.move.is_illegal ? 'illegal' : ''}`}
                    style={{ cursor: white ? 'pointer' : 'default' }}
                  >
                    {white ? white.move.actual_move : ''}
                    {white?.move.is_illegal && <span className="illegal-tag">(Illegal)</span>}
                  </td>

                  {/* Black Move */}
                  <td
                    onClick={() => black && goToMove(black.index)}
                    className={`history-cell ${black && currentMoveIndex === black.index ? 'active' : ''} ${black?.move.is_illegal ? 'illegal' : ''}`}
                    style={{ cursor: black ? 'pointer' : 'default' }}
                  >
                    {black ? black.move.actual_move : ''}
                    {black?.move.is_illegal && <span className="illegal-tag">(Illegal)</span>}
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
