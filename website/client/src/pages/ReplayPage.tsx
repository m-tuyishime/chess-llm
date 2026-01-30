import { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Chessboard } from 'react-chessboard';
import { Chess } from 'chess.js';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, ArrowRight, SkipBack, SkipForward, Menu, X, ExternalLink } from 'lucide-react';
import { api } from '../api/client';
import { GameResponse, PuzzleResponse } from '../api/types';
import { useChessReplay } from '../hooks/useChessReplay';
import { AnalysisBanner } from '../components/AnalysisBanner';
import { MoveHistory } from '../components/MoveHistory';
import { BoardArrows } from '../components/BoardArrows';
import './ReplayPage.css';

/**
 * Page component for replaying a chess game/puzzle.
 * Handles fetching game data, maintaining state, and rendering the board and controls.
 * @returns The ReplayPage component.
 */
export function ReplayPage() {
  const { t } = useTranslation();
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
  const [puzzleStartColor, setPuzzleStartColor] = useState<'white' | 'black'>('white');
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

        // Determine Puzzle Start Color (for MoveHistory)
        const startChess = new Chess(puzzleFen || undefined);
        setPuzzleStartColor(startChess.turn() === 'w' ? 'white' : 'black');

        // Determine Agent Color
        // Look for the first move with tokens (Agent's move)
        const firstAgentMove = gameData.moves.find(
          (m) => (m.completion_tokens || 0) > 0 || (m.prompt_tokens || 0) > 0
        );

        if (firstAgentMove) {
          const index = gameData.moves.indexOf(firstAgentMove);
          const tempChess = new Chess(puzzleFen || undefined);
          for (let i = 0; i < index; i++) {
            try {
              tempChess.move(gameData.moves[i].actual_move);
            } catch {
              // Ignore invalid setup moves
            }
          }
          setAgentColor(tempChess.turn() === 'w' ? 'white' : 'black');
        } else if (puzzleFen) {
          const tokens = puzzleFen.split(' ');
          const sideToMove = tokens[1];
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
  const gameMoves = useMemo(() => game?.moves || [], [game]);
  const {
    boardPosition,
    arrows,
    customSquareStyles,
    currentMoveIndex,
    goToMove,
    hallucinatedSquare,
    illegalSquare,
    analysisResult,
  } = useChessReplay({
    initialFen,
    gameMoves,
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
        {t('common.loading')}
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
        {t('common.error')}: {error}
      </div>
    );
  if (!game)
    return (
      <div
        className="replay-full-screen"
        style={{ justifyContent: 'center', alignItems: 'center' }}
      >
        {t('common.noData')}
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
                squareStyles: customSquareStyles,
                boardStyle: { borderRadius: '4px', boxShadow: 'none' },
                darkSquareStyle: { backgroundColor: '#334155' },
                lightSquareStyle: { backgroundColor: '#94a3b8' },
              }}
            />
            <BoardArrows arrows={arrows} orientation={agentColor} agentColor={agentColor} />
          </div>
        </div>

        <div className="replay-controls">
          <button
            onClick={() => goToMove(-1)}
            disabled={currentMoveIndex === -1}
            className="btn-control"
            aria-label={t('replay.controls.first')}
          >
            <SkipBack size={24} />
          </button>
          <button
            onClick={() => goToMove(currentMoveIndex - 1)}
            disabled={currentMoveIndex === -1}
            className="btn-control"
            aria-label={t('replay.controls.prev')}
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
            aria-label={t('replay.controls.next')}
          >
            <ArrowRight size={24} />
          </button>
          <button
            onClick={() => goToMove(game.moves.length - 1)}
            disabled={currentMoveIndex >= game.moves.length - 1}
            className="btn-control"
            aria-label={t('replay.controls.last')}
          >
            <SkipForward size={24} />
          </button>
        </div>

        <div className="keyboard-legend">
          <small>
            ← / → : {t('replay.controls.prev')}/{t('replay.controls.next')}
          </small>
        </div>
      </div>

      {/* Sidebar */}
      <div className={`replay-sidebar-wrapper ${!isSidebarOpen ? 'collapsed' : ''}`}>
        <div className="sidebar-inner-content">
          {/* Header */}
          <div className="sidebar-header-main">
            <div className="sidebar-nav">
              <button
                onClick={() =>
                  navigate(game?.agent_name ? `/agent/${game.agent_name}` : '/leaderboard')
                }
                className="btn-control btn-back-agent"
                aria-label={t('replay.backToAgent')}
              >
                <ArrowLeft size={16} className="mr-2" /> {t('replay.backToAgent')}
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
              <h1 className="replay-title sidebar-title">
                {game.agent_name || 'Agent'} {t('replay.gameDetails')}
              </h1>
              <p className="sidebar-subtitle">
                {new Date(game.date).toLocaleDateString()} •{' '}
                {game.failed ? t('replay.failed') : t('replay.success')}
              </p>
              <div className="agent-badge">
                <span>Playing as:</span>
                <span className={`agent-badge-color ${agentColor}`}>{agentColor}</span>
              </div>
            </div>
          </div>

          {/* Analysis */}
          <div className="sidebar-section">
            <div className="sidebar-section-header">
              {t('analytics.charts.puzzleOutcomes.title')}
              {game.failed && (
                <span style={{ color: 'var(--status-failed-text)', fontSize: '0.75rem' }}>
                  {t('replay.failed').toUpperCase()}
                </span>
              )}
            </div>
            <div style={{ padding: '1rem' }}>
              {puzzle && (
                <div className="puzzle-meta">
                  <div className="puzzle-stat-row">
                    <div>
                      <div className="stat-label">{t('leaderboard.table.rating')}</div>
                      <div className="stat-value">{puzzle.rating}</div>
                    </div>
                    <div className="puzzle-stat-right">
                      <div className="stat-label">Popularity</div>
                      <div className="stat-value">{puzzle.popularity}%</div>
                    </div>
                  </div>

                  <div className="puzzle-id-box">
                    <div>
                      <div className="stat-label stat-label-sm">{t('replay.puzzleId')}</div>
                      <div className="stat-value puzzle-id-value">{puzzle.id}</div>
                    </div>
                    <a
                      href={`https://lichess.org/training/${puzzle.id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-control btn-open-lichess"
                      title={t('replay.viewOnLichess')}
                      aria-label={t('replay.viewOnLichess')}
                    >
                      <ExternalLink size={14} />
                      Open
                    </a>
                  </div>
                </div>
              )}

              <AnalysisBanner
                currentMove={currentMoveIndex >= 0 ? game?.moves[currentMoveIndex] : null}
                hallucinatedSquare={hallucinatedSquare}
                illegalSquare={illegalSquare}
                analysisResult={analysisResult || undefined}
              />
            </div>
          </div>

          {/* Move History */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            <MoveHistory
              moves={game.moves}
              currentMoveIndex={currentMoveIndex}
              goToMove={goToMove}
              startColor={puzzleStartColor}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
