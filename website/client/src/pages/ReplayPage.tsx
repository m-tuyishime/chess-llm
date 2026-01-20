import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Chessboard } from 'react-chessboard';
import { Chess } from 'chess.js';
import { api } from '../api/client';
import { GameResponse, PuzzleResponse } from '../api/types';
import { ArrowLeft, ArrowRight, SkipBack, SkipForward, Menu, X } from 'lucide-react';
import './ReplayPage.css';

// Define Arrow type locally if not easily importable
type Arrow = {
  startSquare: string;
  endSquare: string;
  color: string;
};

/**
 * ReplayPage Component
 *
 * Displays a detailed replay of a chess game with move history, analysis, and puzzle data.
 * Features a collapsible sidebar and premium V6 UI styling (Full-height sidebar, Flex layout).
 */
export function ReplayPage() {
  const { gameId } = useParams<{ gameId: string }>();
  const navigate = useNavigate();
  const [game, setGame] = useState<GameResponse | null>(null);
  const [puzzle, setPuzzle] = useState<PuzzleResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Chess logic state
  const [chess] = useState(new Chess());
  const [currentMoveIndex, setCurrentMoveIndex] = useState(-1);
  const [boardPosition, setBoardPosition] = useState(chess.fen());
  const [history, setHistory] = useState<string[]>([]);
  const [arrows, setArrows] = useState<Arrow[]>([]);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  useEffect(() => {
    /**
     * Loads game and puzzle data, replaying history to validate moves.
     */
    async function loadData() {
      if (!gameId) return;
      try {
        setLoading(true);
        const gameData = await api.getGame(gameId);
        setGame(gameData);

        let initialFen = '';
        if (gameData.puzzle_id) {
          const puzzleData = await api.getPuzzle(gameData.puzzle_id);
          setPuzzle(puzzleData);
          initialFen = puzzleData.fen;
        }

        if (initialFen) {
          chess.load(initialFen);
        } else {
          chess.reset();
        }

        const validMoves: string[] = [];
        for (const record of gameData.moves) {
          if (record.actual_move) validMoves.push(record.actual_move);
        }

        // Replay full game to validate history
        for (const move of validMoves) {
          try {
            chess.move(move);
          } catch (err) {
            console.error(`Invalid move in history: ${move}`, err);
          }
        }

        setHistory(chess.history());

        // Reset to puzzle start for initial view
        if (initialFen) {
          chess.load(initialFen);
        } else {
          chess.reset();
        }
        setBoardPosition(chess.fen());
        setCurrentMoveIndex(-1);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Failed to fetch game data';
        setError(message);
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [gameId, chess]);

  const updateArrows = (index: number) => {
    const moveRecord = game?.moves[index];
    if (!moveRecord) {
      setArrows([]);
      return;
    }

    const newArrows: Arrow[] = [];
    if (moveRecord.expected_move) {
      const tempChess = new Chess();
      for (let i = 0; i < index; i++) tempChess.move(history[i]);

      // Expected Move (Green)
      try {
        const expected = tempChess.move(moveRecord.expected_move);
        if (expected) {
          newArrows.push({
            startSquare: expected.from,
            endSquare: expected.to,
            color: 'rgba(34, 197, 94, 0.9)', // Superior Green
          });
        }
      } catch (err) {
        console.warn('Invalid expected move:', moveRecord.expected_move, err);
      }

      tempChess.undo();

      // Actual Move (Red) - IF different
      try {
        const actual = tempChess.move(history[index]);
        if (actual && history[index] !== moveRecord.expected_move) {
          newArrows.push({
            startSquare: actual.from,
            endSquare: actual.to,
            color: 'rgba(239, 68, 68, 0.9)', // Superior Red
          });
        }
      } catch (err) {
        console.warn('Invalid actual move:', history[index], err);
      }
    }
    setArrows(newArrows);
  };

  const goToMove = (index: number) => {
    const targetIndex = Math.max(-1, Math.min(index, history.length - 1));
    chess.reset();
    for (let i = 0; i <= targetIndex; i++) {
      chess.move(history[i]);
    }
    setBoardPosition(chess.fen());
    setCurrentMoveIndex(targetIndex);
    updateArrows(targetIndex);
  };

  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, []);

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'ArrowRight') goToMove(currentMoveIndex + 1);
    if (e.key === 'ArrowLeft') goToMove(currentMoveIndex - 1);
  };

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentMoveIndex, history]);

  if (loading)
    return (
      <div
        className="replay-full-screen"
        style={{ justifyContent: 'center', alignItems: 'center' }}
      >
        Loading...
      </div>
    );
  if (error)
    return (
      <div
        className="replay-full-screen"
        style={{
          justifyContent: 'center',
          alignItems: 'center',
          color: 'var(--status-failed-text)',
        }}
      >
        Error: {error}
      </div>
    );
  if (!game)
    return (
      <div
        className="replay-full-screen"
        style={{ justifyContent: 'center', alignItems: 'center' }}
      >
        Game not found
      </div>
    );

  return (
    <div className="replay-full-screen">
      {/* Center: Board + Controls */}
      <div className="replay-center">
        {/* Hamburger Toggle (Visible when closed) */}
        {!isSidebarOpen && (
          <button
            onClick={() => setIsSidebarOpen(true)}
            className="hamburger-btn"
            aria-label="Open Sidebar"
          >
            <Menu size={24} />
          </button>
        )}

        <div className="board-wrapper">
          <div className="board-container">
            <Chessboard
              // @ts-expect-error - position prop is missing in some react-chessboard type versions
              position={boardPosition}
              animationDuration={250}
              customArrows={arrows}
              customBoardStyle={{
                borderRadius: '4px',
                boxShadow: 'none',
              }}
              customDarkSquareStyle={{ backgroundColor: '#334155' }}
              customLightSquareStyle={{ backgroundColor: '#94a3b8' }}
            />
          </div>
        </div>

        <div className="replay-controls">
          <button
            onClick={() => goToMove(-1)}
            disabled={currentMoveIndex === -1}
            className="btn-control"
            aria-label="First Move"
          >
            <SkipBack size={24} />
          </button>
          <button
            onClick={() => goToMove(currentMoveIndex - 1)}
            disabled={currentMoveIndex === -1}
            className="btn-control"
            aria-label="Previous Move"
          >
            <ArrowLeft size={24} />
          </button>

          <div className="move-indicator">
            <span className="move-current">{currentMoveIndex + 1}</span>
            <span className="move-total"> / {history.length}</span>
          </div>

          <button
            onClick={() => goToMove(currentMoveIndex + 1)}
            disabled={currentMoveIndex === history.length - 1}
            className="btn-control"
            aria-label="Next Move"
          >
            <ArrowRight size={24} />
          </button>
          <button
            onClick={() => goToMove(history.length - 1)}
            disabled={currentMoveIndex === history.length - 1}
            className="btn-control"
            aria-label="Last Move"
          >
            <SkipForward size={24} />
          </button>
        </div>
      </div>

      {/* Right Sidebar: Combined Analysis & History */}
      <div className={`replay-sidebar-wrapper ${!isSidebarOpen ? 'collapsed' : ''}`}>
        <div className="sidebar-inner-content">
          {/* Sidebar Header (Title + Back) */}
          <div className="sidebar-header-main">
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                marginBottom: '1rem',
              }}
            >
              <button
                onClick={() => navigate(-1)}
                className="btn-control"
                style={{
                  borderRadius: 'var(--radius-sm)',
                  width: 'auto',
                  padding: '0.25rem 0.5rem',
                  fontSize: '0.875rem',
                }}
              >
                <ArrowLeft size={16} className="mr-2" />
                Back
              </button>

              <button
                onClick={() => setIsSidebarOpen(false)}
                className="btn-control"
                aria-label="Close Sidebar"
              >
                <X size={20} />
              </button>
            </div>

            <div>
              <h1 className="replay-title" style={{ fontSize: '1.1rem', marginBottom: '0.25rem' }}>
                {game.agent_name || 'Agent'} Replay
              </h1>
              <p
                style={{
                  color: 'var(--text-secondary)',
                  fontSize: '0.75rem',
                  fontFamily: 'monospace',
                }}
              >
                {new Date(game.date).toLocaleDateString()} • {game.failed ? 'Failed' : 'Solved'}
              </p>
            </div>
          </div>

          {/* Section: Analysis */}
          <div className="sidebar-section">
            <div className="sidebar-section-header">
              Analysis
              {game.failed && (
                <span style={{ color: 'var(--status-failed-text)', fontSize: '0.75rem' }}>
                  FAILED
                </span>
              )}
            </div>
            <div style={{ padding: '1rem' }}>
              {puzzle && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <div>
                      <div
                        className="stat-label has-tooltip tooltip-left"
                        data-tooltip="The chess Elo rating of the original puzzle."
                      >
                        Rating
                      </div>
                      <div className="stat-value" style={{ fontSize: '1.25rem' }}>
                        {puzzle.rating}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div
                        className="stat-label has-tooltip tooltip-right"
                        data-tooltip="Percentage of users who liked this puzzle on Lichess."
                      >
                        Popularity
                      </div>
                      <div className="stat-value" style={{ fontSize: '1.25rem' }}>
                        {puzzle.popularity}%
                      </div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                    {puzzle.themes.split(' ').map((t) => (
                      <span key={t} className="badge badge-info">
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {game.failed && (
                <div
                  style={{
                    marginTop: '1rem',
                    padding: '0.75rem',
                    background: 'rgba(239, 68, 68, 0.1)',
                    borderLeft: '4px solid #ef4444',
                    borderRadius: '4px',
                  }}
                >
                  <div style={{ color: '#ef4444', fontWeight: 'bold', fontSize: '0.875rem' }}>
                    Incorrect Move
                  </div>
                  <div style={{ color: '#fca5a5', fontSize: '0.75rem' }}>
                    The agent did not play the optimal line.
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Section: Move History */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            <div
              className="sidebar-section-header has-tooltip"
              style={{ background: 'var(--bg-app)' }}
              data-tooltip="A complete chronological history of every move played in this game."
            >
              Move Records
            </div>
            <div className="replay-sidebar-content custom-scrollbar">
              <table
                style={{
                  width: '100%',
                  borderCollapse: 'collapse',
                  fontFamily: 'monospace',
                  fontSize: '0.9rem',
                }}
              >
                <thead
                  style={{ position: 'sticky', top: 0, background: 'var(--bg-card)', zIndex: 10 }}
                >
                  <tr>
                    <th
                      style={{
                        padding: '0.75rem 1rem',
                        textAlign: 'left',
                        color: 'var(--text-tertiary)',
                        fontWeight: 600,
                        borderBottom: '1px solid var(--border-subtle)',
                      }}
                    >
                      #
                    </th>
                    <th
                      style={{
                        padding: '0.75rem',
                        textAlign: 'left',
                        color: 'var(--text-secondary)',
                        fontWeight: 600,
                        borderBottom: '1px solid var(--border-subtle)',
                      }}
                    >
                      White
                    </th>
                    <th
                      style={{
                        padding: '0.75rem',
                        textAlign: 'left',
                        color: 'var(--text-secondary)',
                        fontWeight: 600,
                        borderBottom: '1px solid var(--border-subtle)',
                      }}
                    >
                      Black
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {Array.from({ length: Math.ceil(history.length / 2) }).map((_, i) => {
                    const whiteMoveIndex = i * 2;
                    const blackMoveIndex = i * 2 + 1;
                    const whiteMove = history[whiteMoveIndex];
                    const blackMove = history[blackMoveIndex];
                    const isCurrentRow = Math.floor(currentMoveIndex / 2) === i;

                    return (
                      <tr
                        key={i}
                        style={{
                          background: isCurrentRow ? 'rgba(255,255,255,0.03)' : 'transparent',
                          borderBottom: '1px solid var(--border-subtle)',
                        }}
                      >
                        <td style={{ padding: '0.75rem 1rem', color: 'var(--text-tertiary)' }}>
                          {i + 1}.
                        </td>
                        <td
                          onClick={() => goToMove(whiteMoveIndex)}
                          className="history-cell"
                          style={{
                            padding: '0.75rem',
                            cursor: 'pointer',
                            color:
                              currentMoveIndex === whiteMoveIndex
                                ? 'var(--accent-primary)'
                                : 'var(--text-primary)',
                            fontWeight: currentMoveIndex === whiteMoveIndex ? 'bold' : 'normal',
                            background:
                              currentMoveIndex === whiteMoveIndex
                                ? 'rgba(59,130,246,0.1)'
                                : 'transparent',
                          }}
                        >
                          {whiteMove}
                        </td>
                        <td
                          onClick={() => blackMove && goToMove(blackMoveIndex)}
                          className="history-cell"
                          style={{
                            padding: '0.75rem',
                            cursor: 'pointer',
                            color:
                              currentMoveIndex === blackMoveIndex
                                ? 'var(--accent-primary)'
                                : 'var(--text-primary)',
                            fontWeight: currentMoveIndex === blackMoveIndex ? 'bold' : 'normal',
                            background:
                              currentMoveIndex === blackMoveIndex
                                ? 'rgba(59,130,246,0.1)'
                                : 'transparent',
                          }}
                        >
                          {blackMove || ''}
                        </td>
                      </tr>
                    );
                  })}
                  {history.length === 0 && (
                    <tr>
                      <td
                        colSpan={3}
                        style={{
                          padding: '2rem',
                          textAlign: 'center',
                          color: 'var(--text-tertiary)',
                        }}
                      >
                        No moves yet
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
              <div style={{ height: '2rem' }}></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
