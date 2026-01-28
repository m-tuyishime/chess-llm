import { Arrow } from '../hooks/useChessReplay';

interface BoardArrowsProps {
  arrows: Arrow[];
  orientation: 'white' | 'black';
  agentColor: 'white' | 'black';
}

const VIEWBOX_SIZE = 2048;
const BOARD_SIZE = 8;
const ARROW_WIDTH_DENOMINATOR = 5;
const ARROW_OPACITY = 0.65;
const CORNER_RADIUS_DIVISOR = 8;
const ARROW_BORDER_SCALE = 1.2;
const ARROW_HEAD_LENGTH_FACTOR = 1.2;
const ARROW_HEAD_HALF_HEIGHT_FACTOR = 1.1;

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
  const tipX = ARROW_HEAD_LENGTH_FACTOR * strokeWidth;
  const baseX = 0;
  const halfH = ARROW_HEAD_HALF_HEIGHT_FACTOR * strokeWidth;
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

  const squareWidth = VIEWBOX_SIZE / BOARD_SIZE;
  const strokeWidth = squareWidth / ARROW_WIDTH_DENOMINATOR;
  const borderStrokeWidth = strokeWidth * ARROW_BORDER_SCALE;
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
        zIndex: 1,
      }}
    >
      {arrows.map((arrow, i) => {
        const from = getSquareCenter(arrow.startSquare, orientation, squareWidth);
        const to = getSquareCenter(arrow.endSquare, orientation, squareWidth);

        // Calculate offset to separate arrows with same start/end
        // We set this to 0,0 to ensure arrows start/end at the exact center of tiles
        // const offset = getArrowOffset(arrows, arrow, i, from, to, strokeWidth);
        const offset = { x: 0, y: 0 };

        const fromWithOffset = { x: from.x + offset.x, y: from.y + offset.y };
        const toWithOffset = { x: to.x + offset.x, y: to.y + offset.y };

        const dx = toWithOffset.x - fromWithOffset.x;
        const dy = toWithOffset.y - fromWithOffset.y;

        const isStraight = dx === 0 || dy === 0 || Math.abs(dx) === Math.abs(dy);

        const lengthReducer = ARROW_HEAD_LENGTH_FACTOR * strokeWidth;

        let pathD = '';
        let arrowAngleDeg = 0;
        let arrowEnd = toWithOffset;

        if (!isStraight) {
          const mid =
            Math.abs(dx) < Math.abs(dy)
              ? { x: fromWithOffset.x, y: toWithOffset.y }
              : { x: toWithOffset.x, y: fromWithOffset.y };

          const dxEnd = toWithOffset.x - mid.x;
          const dyEnd = toWithOffset.y - mid.y;
          const rEnd = Math.hypot(dxEnd, dyEnd);

          arrowEnd =
            rEnd > lengthReducer
              ? {
                  x: mid.x + (dxEnd * (rEnd - lengthReducer)) / rEnd,
                  y: mid.y + (dyEnd * (rEnd - lengthReducer)) / rEnd,
                }
              : toWithOffset;

          const seg1Len = Math.hypot(mid.x - fromWithOffset.x, mid.y - fromWithOffset.y) || 1;
          const seg2Len = Math.hypot(arrowEnd.x - mid.x, arrowEnd.y - mid.y) || 1;
          const adjustedCornerRadius = Math.min(cornerRadius, seg1Len / 2, seg2Len / 2);

          const cornerStart = {
            x: mid.x - ((mid.x - fromWithOffset.x) / seg1Len) * adjustedCornerRadius,
            y: mid.y - ((mid.y - fromWithOffset.y) / seg1Len) * adjustedCornerRadius,
          };
          const cornerEnd = {
            x: mid.x + ((arrowEnd.x - mid.x) / seg2Len) * adjustedCornerRadius,
            y: mid.y + ((arrowEnd.y - mid.y) / seg2Len) * adjustedCornerRadius,
          };

          pathD = `M ${fromWithOffset.x},${fromWithOffset.y} L ${cornerStart.x},${cornerStart.y} Q ${mid.x},${mid.y} ${cornerEnd.x},${cornerEnd.y} L ${arrowEnd.x},${arrowEnd.y}`;

          const angleRad = Math.atan2(arrowEnd.y - cornerEnd.y, arrowEnd.x - cornerEnd.x);
          arrowAngleDeg = (angleRad * 180) / Math.PI;
        } else {
          const r = Math.hypot(dx, dy);
          arrowEnd =
            r > lengthReducer
              ? {
                  x: fromWithOffset.x + (dx * (r - lengthReducer)) / r,
                  y: fromWithOffset.y + (dy * (r - lengthReducer)) / r,
                }
              : toWithOffset;

          pathD = `M ${fromWithOffset.x},${fromWithOffset.y} L ${arrowEnd.x},${arrowEnd.y}`;

          const angleRad = Math.atan2(arrowEnd.y - fromWithOffset.y, arrowEnd.x - fromWithOffset.x);
          arrowAngleDeg = (angleRad * 180) / Math.PI;
        }

        const isRed = arrow.color.includes('239, 68, 68');
        const arrowHeadPoints = buildArrowHeadPoints(strokeWidth);
        const borderArrowHeadPoints = buildArrowHeadPoints(borderStrokeWidth);
        const borderColor = arrow.borderColor || (agentColor === 'white' ? 'white' : 'black');

        return (
          <g
            key={`${arrow.startSquare}-${arrow.endSquare}-${i}`}
            className={isRed ? 'blinking-arrow' : ''}
            style={{ opacity: ARROW_OPACITY }}
          >
            <g>
              <path
                d={pathD}
                stroke={borderColor}
                strokeWidth={borderStrokeWidth}
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeMiterlimit={2}
                shapeRendering="geometricPrecision"
              />
              <polygon
                points={borderArrowHeadPoints}
                fill={borderColor}
                strokeLinejoin="round"
                shapeRendering="geometricPrecision"
                transform={`translate(${arrowEnd.x}, ${arrowEnd.y}) rotate(${arrowAngleDeg})`}
              />
            </g>
            <g>
              <path
                d={pathD}
                stroke={arrow.color}
                strokeWidth={strokeWidth}
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeMiterlimit={2}
                shapeRendering="geometricPrecision"
              />
              <polygon
                points={arrowHeadPoints}
                fill={arrow.color}
                strokeLinejoin="round"
                shapeRendering="geometricPrecision"
                transform={`translate(${arrowEnd.x}, ${arrowEnd.y}) rotate(${arrowAngleDeg})`}
              />
            </g>
          </g>
        );
      })}
    </svg>
  );
}
