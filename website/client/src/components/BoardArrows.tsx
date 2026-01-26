import { Arrow } from '../hooks/useChessReplay';

interface BoardArrowsProps {
  arrows: Arrow[];
  orientation: 'white' | 'black';
  agentColor: 'white' | 'black';
}

const VIEWBOX_SIZE = 2048;
const BOARD_SIZE = 8;
const ARROW_LENGTH_REDUCER_DENOMINATOR = 8;
const SAME_TARGET_LENGTH_REDUCER_DENOMINATOR = 4;
const ARROW_WIDTH_DENOMINATOR = 5;
const ARROW_OPACITY = 0.65;
const CORNER_RADIUS_DIVISOR = 8;

const getSquareCenter = (square: string, orientation: 'white' | 'black', squareWidth: number) => {
  const file = square.charCodeAt(0) - 97; // a=0, h=7
  const rank = parseInt(square[1], 10); // 1-8

  const columnIndex = orientation === 'white' ? file : BOARD_SIZE - 1 - file;
  const rowIndex = orientation === 'white' ? BOARD_SIZE - rank : rank - 1;

  return {
    x: columnIndex * squareWidth + squareWidth / 2,
    y: rowIndex * squareWidth + squareWidth / 2,
  };
};

const buildArrowHeadPoints = (strokeWidth: number) => {
  const tipX = 0.75 * strokeWidth;
  const baseX = -0.95 * strokeWidth;
  const halfH = 1.25 * strokeWidth;
  return `${tipX},0 ${baseX},-${halfH} ${baseX},${halfH}`;
};

/**
 * Component to render custom chess board arrows with curved corners and borders.
 * @param props - The component props.
 * @param props.arrows - The list of arrows to render.
 * @param props.orientation - The orientation of the board.
 * @param props.agentColor - The color of the agent (used for arrow borders).
 * @returns The BoardArrows component.
 */
export function BoardArrows({ arrows, orientation, agentColor }: BoardArrowsProps) {
  if (arrows.length === 0) return null;

  const borderColor = agentColor === 'white' ? 'white' : 'black';
  const squareWidth = VIEWBOX_SIZE / BOARD_SIZE;
  const strokeWidth = squareWidth / ARROW_WIDTH_DENOMINATOR;
  const borderStrokeWidth = strokeWidth * 1.3;
  const cornerRadius = squareWidth / CORNER_RADIUS_DIVISOR;

  return (
    <svg
      viewBox={`0 0 ${VIEWBOX_SIZE} ${VIEWBOX_SIZE}`}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 20,
      }}
    >
      {arrows.map((arrow, i) => {
        const from = getSquareCenter(arrow.startSquare, orientation, squareWidth);
        const to = getSquareCenter(arrow.endSquare, orientation, squareWidth);

        const dx = to.x - from.x;
        const dy = to.y - from.y;

        const isStraight = dx === 0 || dy === 0 || Math.abs(dx) === Math.abs(dy);
        const sameTarget = arrows.some(
          (other, idx) =>
            idx !== i &&
            other.startSquare !== arrow.startSquare &&
            other.endSquare === arrow.endSquare
        );

        const lengthReducer =
          squareWidth /
          (sameTarget ? SAME_TARGET_LENGTH_REDUCER_DENOMINATOR : ARROW_LENGTH_REDUCER_DENOMINATOR);

        let pathD = '';
        let arrowAngleDeg = 0;
        let arrowEnd = to;

        if (!isStraight) {
          const mid = Math.abs(dx) < Math.abs(dy) ? { x: from.x, y: to.y } : { x: to.x, y: from.y };

          const dxEnd = to.x - mid.x;
          const dyEnd = to.y - mid.y;
          const rEnd = Math.hypot(dxEnd, dyEnd);

          arrowEnd =
            rEnd > lengthReducer
              ? {
                  x: mid.x + (dxEnd * (rEnd - lengthReducer)) / rEnd,
                  y: mid.y + (dyEnd * (rEnd - lengthReducer)) / rEnd,
                }
              : to;

          const seg1Len = Math.hypot(mid.x - from.x, mid.y - from.y) || 1;
          const seg2Len = Math.hypot(arrowEnd.x - mid.x, arrowEnd.y - mid.y) || 1;
          const adjustedCornerRadius = Math.min(cornerRadius, seg1Len / 2, seg2Len / 2);

          const cornerStart = {
            x: mid.x - ((mid.x - from.x) / seg1Len) * adjustedCornerRadius,
            y: mid.y - ((mid.y - from.y) / seg1Len) * adjustedCornerRadius,
          };
          const cornerEnd = {
            x: mid.x + ((arrowEnd.x - mid.x) / seg2Len) * adjustedCornerRadius,
            y: mid.y + ((arrowEnd.y - mid.y) / seg2Len) * adjustedCornerRadius,
          };

          pathD = `M ${from.x},${from.y} L ${cornerStart.x},${cornerStart.y} Q ${mid.x},${mid.y} ${cornerEnd.x},${cornerEnd.y} L ${arrowEnd.x},${arrowEnd.y}`;

          const angleRad = Math.atan2(arrowEnd.y - cornerEnd.y, arrowEnd.x - cornerEnd.x);
          arrowAngleDeg = (angleRad * 180) / Math.PI;
        } else {
          const r = Math.hypot(dx, dy);
          arrowEnd =
            r > lengthReducer
              ? {
                  x: from.x + (dx * (r - lengthReducer)) / r,
                  y: from.y + (dy * (r - lengthReducer)) / r,
                }
              : to;

          pathD = `M ${from.x},${from.y} L ${arrowEnd.x},${arrowEnd.y}`;

          const angleRad = Math.atan2(arrowEnd.y - from.y, arrowEnd.x - from.x);
          arrowAngleDeg = (angleRad * 180) / Math.PI;
        }

        const isRed = arrow.color.includes('239, 68, 68');
        const arrowHeadPoints = buildArrowHeadPoints(strokeWidth);
        const borderArrowHeadPoints = buildArrowHeadPoints(borderStrokeWidth);

        return (
          <g
            key={`${arrow.startSquare}-${arrow.endSquare}-${i}`}
            className={isRed ? 'blinking-arrow' : ''}
            style={{ opacity: ARROW_OPACITY }}
          >
            <g>
              <path d={pathD} stroke={borderColor} strokeWidth={borderStrokeWidth} fill="none" />
              <polygon
                points={borderArrowHeadPoints}
                fill={borderColor}
                transform={`translate(${arrowEnd.x}, ${arrowEnd.y}) rotate(${arrowAngleDeg})`}
              />
            </g>
            <g>
              <path d={pathD} stroke={arrow.color} strokeWidth={strokeWidth} fill="none" />
              <polygon
                points={arrowHeadPoints}
                fill={arrow.color}
                transform={`translate(${arrowEnd.x}, ${arrowEnd.y}) rotate(${arrowAngleDeg})`}
              />
            </g>
          </g>
        );
      })}
    </svg>
  );
}
