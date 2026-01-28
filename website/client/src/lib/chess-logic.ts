import { Chess, PieceSymbol, Color, Square } from 'chess.js';

export const ARROW_COLOR_RED = 'rgba(239, 68, 68, 0.9)';
export const ARROW_COLOR_GREEN = 'rgba(34, 197, 94, 0.9)';

/**
 * Parsed components of a SAN move string
 */
export interface ParsedMove {
  san: string;
  pieceType: PieceSymbol;
  targetSquare: string;
  isCapture: boolean;
  isCheck: boolean;
  isMate: boolean;
  promotion?: string;
  disambiguation?: string;
}

/**
 * Parses a chess move string (SAN or UCI).
 * @param san The move string to parse (e.g., 'e4', 'Nf3', 'e2e4')
 */
export function parseMove(san: string): ParsedMove | null {
  if (!san) return null;

  // Clean move string (remove suffixes like +, #, ?, !)
  const cleanSan = san.replace(/[+#?!]/g, '');

  // 1. Try to parse as UCI (e.g., e2e4, e7e8q)
  const uciMatch = cleanSan.match(/^([a-h][1-8])([a-h][1-8])([qrbn])?$/);
  if (uciMatch) {
    return {
      san,
      pieceType: 'p', // Placeholder, corrected by caller with board context
      targetSquare: uciMatch[2],
      isCapture: false,
      isCheck: san.includes('+'),
      isMate: san.includes('#'),
      promotion: uciMatch[3],
      disambiguation: uciMatch[1],
    };
  }

  // 2. Standard regex for SAN (simplified but handling disambiguation)
  const match = cleanSan.match(/^([RNBQK])?([a-h1-8]{0,2})?(x)?([a-h][1-8])(=[RNBQ])?$/);

  if (match) {
    const pieceChar = match[1] || 'P';
    return {
      san,
      pieceType: pieceChar.toLowerCase() as PieceSymbol,
      targetSquare: match[4],
      isCapture: !!match[3],
      isCheck: san.includes('+'),
      isMate: san.includes('#'),
      promotion: match[5] ? match[5].substring(1) : undefined,
      disambiguation: match[2] || undefined,
    };
  }

  // 3. Special case: Castling
  if (cleanSan === 'O-O' || cleanSan === '0-0') {
    return {
      san,
      pieceType: 'k',
      targetSquare: 'g',
      isCapture: false,
      isCheck: san.includes('+'),
      isMate: san.includes('#'),
    };
  }
  if (cleanSan === 'O-O-O' || cleanSan === '0-0-0') {
    return {
      san,
      pieceType: 'k',
      targetSquare: 'c',
      isCapture: false,
      isCheck: san.includes('+'),
      isMate: san.includes('#'),
    };
  }

  return null;
}

/**
 * Result of illegal move analysis
 */
export interface IllegalMoveAnalysis {
  type: 'legal' | 'hallucination' | 'illegal' | 'unknown';
  pieceType?: PieceSymbol;
  targetSquare: string | null;
  sourceSquare?: string;
  description: string;
}

/**
 * Analyzes a potential illegal move to determine if it's a "Hallucination"
 * or just a rule/notation violation.
 * @param fen The current board position in FEN format
 * @param moveSan The illegal move string in SAN or UCI
 * @param agentColor The color of the agent making the move ('white' or 'black')
 */
export function analyzeIllegalMove(
  fen: string,
  moveSan: string,
  agentColor: 'white' | 'black'
): IllegalMoveAnalysis {
  const parsed = parseMove(moveSan);
  if (!parsed) {
    return {
      type: 'unknown',
      targetSquare: null,
      description: `The agent played an unrecognizable move string: "${moveSan}".`,
    };
  }

  const chess = new Chess(fen);
  const board = chess.board();
  const turnColor = agentColor === 'white' ? 'w' : 'b';

  // 1. Collect ALL pieces of this type on the board
  const allPiecesOfThisType: { type: PieceSymbol; color: Color; square: Square }[] = [];
  for (let r = 0; r < 8; r++) {
    for (let c = 0; c < 8; c++) {
      const p = board[r][c];
      if (p && p.type === parsed.pieceType) {
        allPiecesOfThisType.push({
          type: p.type,
          color: p.color as Color,
          square: p.square as Square,
        });
      }
    }
  }

  // If it was UCI, determine the actual piece type from the board
  const cleanSan = moveSan.replace(/[+#?!]/g, '');
  const uciMatch = cleanSan.match(/^([a-h][1-8])([a-h][1-8])([qrbn])?$/);
  if (uciMatch) {
    const from = uciMatch[1];
    const pieceAtSource = chess.get(from as Square);
    if (pieceAtSource) {
      parsed.pieceType = pieceAtSource.type;
    }
  }

  const playerPieces = allPiecesOfThisType.filter((p) => p.color === turnColor);
  let sourceSquare: string | null = null;

  // 2. Identify intended source
  if (parsed.disambiguation) {
    const match = playerPieces.find((p) => p.square.includes(parsed.disambiguation!));
    if (match) {
      sourceSquare = match.square;
    }
  } else if (playerPieces.length === 1) {
    sourceSquare = playerPieces[0].square;
  }

  // 3. Check if the move is actually legal with the identified source
  if (sourceSquare) {
    const testChess = new Chess(fen);
    try {
      const moveResult = testChess.move({
        from: sourceSquare,
        to: parsed.targetSquare,
        promotion: parsed.promotion,
      });
      if (moveResult) {
        return {
          type: 'legal',
          pieceType: parsed.pieceType,
          targetSquare: parsed.targetSquare,
          sourceSquare,
          description: `The agent played ${moveSan}.`,
        };
      }
    } catch {
      // Identified piece cannot move there legally
    }
  }

  // 4. Handle Disambiguation Mismatch / Hallucination
  if (parsed.disambiguation) {
    const anyMatchingPiece = allPiecesOfThisType.find((p) =>
      p.square.includes(parsed.disambiguation!)
    );
    if (anyMatchingPiece) {
      const isWrongColor = anyMatchingPiece.color !== turnColor;
      return {
        type: 'illegal',
        pieceType: parsed.pieceType,
        targetSquare: parsed.targetSquare,
        sourceSquare: anyMatchingPiece.square,
        description: isWrongColor
          ? `The agent tried to move the ${parsed.pieceType.toUpperCase()} on ${anyMatchingPiece.square}, but that piece belongs to the opponent! (Ownership Hallucination)`
          : `The agent tried to move its ${parsed.pieceType.toUpperCase()} on ${anyMatchingPiece.square} to ${parsed.targetSquare}, but it's an illegal move.`,
      };
    }

    return {
      type: 'hallucination',
      pieceType: parsed.pieceType,
      targetSquare: parsed.targetSquare,
      description: `The agent tried to move a ${parsed.pieceType.toUpperCase()} from the ${parsed.disambiguation}-file/rank, but it has no such piece there (Location Hallucination).`,
    };
  }

  // 5. Fallback: No disambiguation provided, but move is illegal
  if (playerPieces.length > 0) {
    const legalMoves = chess.moves({ verbose: true });
    const matchingLegalMove = legalMoves.find(
      (m) => m.piece === parsed.pieceType && m.to === (parsed.targetSquare as Square)
    );
    if (matchingLegalMove) {
      return {
        type: 'legal',
        pieceType: parsed.pieceType,
        targetSquare: parsed.targetSquare,
        sourceSquare: matchingLegalMove.from,
        description: `The agent played ${moveSan}. While the notation is slightly unusual, the move is legal.`,
      };
    }

    return {
      type: 'illegal',
      pieceType: parsed.pieceType,
      targetSquare: parsed.targetSquare,
      sourceSquare: playerPieces[0].square,
      description: `The agent tried to move its ${parsed.pieceType.toUpperCase()} on ${playerPieces[0].square} to ${parsed.targetSquare}, but it's an illegal move.`,
    };
  }

  return {
    type: 'hallucination',
    pieceType: parsed.pieceType,
    targetSquare: parsed.targetSquare,
    description: `The agent tried to move a non-existent ${parsed.pieceType.toUpperCase()} to ${parsed.targetSquare} (Hallucination).`,
  };
}

/**
 * Generates an FEN string representing the "Illegal State" visualization.
 * @param baseFen The original board position
 * @param pieceType The type of piece that was "hallucinated"
 * @param color The color of the piece
 * @param targetSquare The destination square
 */
export function generateIllegalStateFen(
  baseFen: string,
  pieceType: string,
  color: 'w' | 'b',
  targetSquare: string
): string {
  const chess = new Chess(baseFen);
  const success = chess.put(
    { type: pieceType as PieceSymbol, color: color as Color },
    targetSquare as Square
  );
  return success ? chess.fen() : baseFen;
}
