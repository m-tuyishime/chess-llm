import { Chess, PieceSymbol, Color, Square } from 'chess.js';

/**
 * Simulation of the logic in ReplayPage to generate an illegal FEN.
 * @param baseFen - The base FEN string.
 * @param moveSan - The move string in SAN.
 * @param agentColor - The color of the agent.
 * @returns The generated FEN string or null if failed.
 */
function getIllegalFen(baseFen: string, moveSan: string, agentColor: 'white' | 'black') {
  const checkState = new Chess(baseFen);

  // Logic from ReplayPage
  const cleanMove = moveSan.replace(/[+#?!]/g, '');
  const match = cleanMove.match(/^([RNBQK])?.*([a-h][1-8])$/);

  if (!match) {
    console.log('Regex failed for:', moveSan);
    return null;
  }

  const pieceChar = match[1] ? match[1].toLowerCase() : 'p';
  const targetSquare = match[2];
  const turnColor = agentColor === 'white' ? 'w' : 'b';

  console.log(`Analyzing Move: ${moveSan}`);
  console.log(`Target: ${targetSquare}, Piece: ${pieceChar}, Color: ${turnColor}`);

  const board = checkState.board();
  let sourceSquare = null;

  // Find source
  for (let r = 0; r < 8; r++) {
    for (let c = 0; c < 8; c++) {
      const p = board[r][c];
      if (p && p.color === turnColor && p.type === pieceChar) {
        sourceSquare = p.square;
        break;
      }
    }
    if (sourceSquare) break;
  }

  console.log(`Found Source at: ${sourceSquare}`);

  if (sourceSquare && checkState.remove(sourceSquare as Square)) {
    const success = checkState.put(
      { type: pieceChar as PieceSymbol, color: turnColor as Color },
      targetSquare as Square
    );
    if (success) {
      return checkState.fen();
    } else {
      console.log('Put failed');
    }
  } else {
    console.log('Remove failed or source not found');
  }
  return null;
}

// Test Case from Game 10250
// Initial FEN for puzzle (approximate, or just start)
// Game 10250:
// 1. Qg1 ...
// 2. ... Qc6 (Illegal)
// Let's assume start pos or close to it.
const startFen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
new Chess(startFen);
// 1. Qg1 is actually illegal from start, but let's assume a position where Qg1 was played.
// Let's just test "Qc6" from a board where White has a Queen.
const testFen = 'rnbqkbnr/pppppppp/8/8/6Q1/8/PPPPPPPP/RNB1KBNR w KQkq - 0 1'; // Queen at g4

console.log('--- Test 1: Legal-looking illegal move ---');
const newFen = getIllegalFen(testFen, 'Qc6', 'white');
console.log('Base FEN:   ', testFen);
console.log('Illegal FEN:', newFen);

if (newFen === testFen) console.log('FAIL: FENs are identical');
else if (!newFen) console.log('FAIL: No FEN generated');
else console.log('SUCCESS: FEN changed');

// Verify content of new FEN
if (newFen) {
  const c2 = new Chess(newFen);
  const pieceAtC6 = c2.get('c6');
  console.log('Piece at c6:', pieceAtC6);
}
