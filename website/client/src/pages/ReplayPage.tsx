import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Chessboard } from 'react-chessboard';
import { ArrowLeft, ArrowRight, SkipBack, SkipForward, Menu, X } from 'lucide-react';
import { api } from '../api/client';
import { GameResponse, PuzzleResponse } from '../api/types';
import { useChessReplay } from '../hooks/useChessReplay';
import { AnalysisBanner } from '../components/AnalysisBanner';
import { MoveHistory } from '../components/MoveHistory';
import './ReplayPage.css';

/**
 * Page component for replaying a chess game/puzzle.
 * Handles fetching game data, maintaining state, and rendering the board and controls.
 * @returns The ReplayPage component.
 */
export function ReplayPage() {
  const { gameId } = useParams<{ gameId: string }>();
  const navigate = useNavigate();

  // Data State
  const [game, setGame] = useState<GameResponse | null>(null);
  const [puzzle, setPuzzle] = useState<PuzzleResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Config State
  const [initialFen, setInitialFen] = useState<string>('');
  const [agentColor, setAgentColor] = useState<'white' | 'black'>('white');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  // Load Data
  useEffect(() => {
    /**
     * Fetches game and puzzle data from the API.
     */
    async function loadData() {
      if (!gameId) return;
      try {
        setLoading(true);
        const gameData = await api.getGame(gameId);
        setGame(gameData);

        let puzzleFen = '';
        if (gameData.puzzle_id) {
          const puzzleData = await api.getPuzzle(gameData.puzzle_id);
          setPuzzle(puzzleData);
          puzzleFen = puzzleData.fen;
        }

        setInitialFen(puzzleFen);

        if (puzzleFen) {
          // Basic Fen parsing to determine color
          const tokens = puzzleFen.split(' ');
          const sideToMove = tokens[1]; // 'w' or 'b'
          // Agent matches the puzzle solver color (who is about to move)
          // Wait, in Lichess puzzles, FEN is usually start position.
          // Side to move IS the player.
          setAgentColor(sideToMove === 'w' ? 'white' : 'black');
        } else {
          setAgentColor('white');
        }
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Failed to fetch game data';
        setError(message);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [gameId]);

  // Chess Logic Hook
  const {
    boardPosition,
    arrows,
    customSquareStyles,
    currentMoveIndex,
    goToMove,
    hallucinatedSquare,
    illegalSquare,
  } = useChessReplay({
    initialFen,
    gameMoves: game?.moves || [],
    agentColor,
  });

  // Keyboard Navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') goToMove(currentMoveIndex + 1);
      if (e.key === 'ArrowLeft') goToMove(currentMoveIndex - 1);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentMoveIndex, goToMove]);

  // View
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
      {/* Dynamic Styles for Hallucination/Illegal Blink */}
      <style>{`
          ${illegalSquare ? `[data-square="${illegalSquare}"] img, [data-square="${illegalSquare}"] svg { animation: blink-opacity 1s infinite; }` : ''}
          ${hallucinatedSquare ? `[data-square="${hallucinatedSquare}"] img, [data-square="${hallucinatedSquare}"] svg { opacity: 0.5; }` : ''}
      `}</style>

      {/* Center Board */}
      <div className="replay-center">
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
              options={{
                position: boardPosition,
                boardOrientation: agentColor,
                animationDurationInMs: 250,
                arrows: arrows,
                squareStyles: customSquareStyles,
                boardStyle: { borderRadius: '4px', boxShadow: 'none' },
                darkSquareStyle: { backgroundColor: '#334155' },
                lightSquareStyle: { backgroundColor: '#94a3b8' },
              }}
            />
          </div>
        </div>

        <div className="replay-controls">
          <button
            onClick={() => goToMove(-1)}
            disabled={currentMoveIndex === -1}
            className="btn-control"
          >
            <SkipBack size={24} />
          </button>
          <button
            onClick={() => goToMove(currentMoveIndex - 1)}
            disabled={currentMoveIndex === -1}
            className="btn-control"
          >
            <ArrowLeft size={24} />
          </button>

          <div className="move-indicator">
            <span className="move-current">{currentMoveIndex + 1}</span>
            <span className="move-total"> / {game.moves.length}</span>
          </div>

          <button
            onClick={() => goToMove(currentMoveIndex + 1)}
            disabled={currentMoveIndex >= game.moves.length - 1}
            className="btn-control"
          >
            <ArrowRight size={24} />
          </button>
          <button
            onClick={() => goToMove(game.moves.length - 1)}
            disabled={currentMoveIndex >= game.moves.length - 1}
            className="btn-control"
          >
            <SkipForward size={24} />
          </button>
        </div>

        <div className="keyboard-legend">
          <small>← / → : Prev/Next Move</small>
        </div>
      </div>

      {/* Sidebar */}
      <div className={`replay-sidebar-wrapper ${!isSidebarOpen ? 'collapsed' : ''}`}>
        <div className="sidebar-inner-content">
          {/* Header */}
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
                onClick={() =>
                  navigate(game?.agent_name ? `/agent/${game.agent_name}` : '/leaderboard')
                }
                className="btn-control"
                style={{
                  borderRadius: 'var(--radius-sm)',
                  width: 'auto',
                  padding: '0.25rem 0.5rem',
                  fontSize: '0.875rem',
                }}
              >
                <ArrowLeft size={16} className="mr-2" /> Back to Agent
              </button>
              <button onClick={() => setIsSidebarOpen(false)} className="btn-control">
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
                  marginBottom: '0.5rem',
                }}
              >
                {new Date(game.date).toLocaleDateString()} • {game.failed ? 'Failed' : 'Solved'}
              </p>
              <div
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.25rem 0.75rem',
                  background: 'var(--bg-surface)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                }}
              >
                <span>Playing as:</span>
                <span
                  style={{
                    color: agentColor === 'white' ? '#e0e0e0' : '#1a1a1a',
                    background: agentColor === 'white' ? '#ffffff' : '#000000',
                    padding: '0.125rem 0.5rem',
                    borderRadius: '4px',
                    textTransform: 'capitalize',
                  }}
                >
                  {agentColor}
                </span>
              </div>
            </div>
          </div>

          {/* Analysis */}
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
                <div
                  style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}
                >
                  <div>
                    <div className="stat-label">Rating</div>
                    <div className="stat-value">{puzzle.rating}</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div className="stat-label">Popularity</div>
                    <div className="stat-value">{puzzle.popularity}%</div>
                  </div>
                </div>
              )}

              <AnalysisBanner
                currentMove={currentMoveIndex >= 0 ? game?.moves[currentMoveIndex] : null}
                hallucinatedSquare={hallucinatedSquare}
                illegalSquare={illegalSquare}
              />
            </div>
          </div>

          {/* Move History */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            <MoveHistory
              moves={game.moves}
              currentMoveIndex={currentMoveIndex}
              goToMove={goToMove}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
