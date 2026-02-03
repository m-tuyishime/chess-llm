import { useEffect, useState, useMemo } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { api } from '../api/client';
import {
  AgentDetailResponse,
  AgentPuzzleOutcomeResponse,
  BenchmarkDataResponse,
} from '../api/types';
import {
  Trophy,
  Activity,
  Hash,
  Check,
  X,
  ArrowLeft,
  Gamepad2,
  Brain,
  Dice5,
  PieChart,
  TrendingUp,
} from 'lucide-react';
import { ChartCard } from '../components/ChartCard';
import { PuzzleOutcomesChart } from '../components/charts/PuzzleOutcomesChart';
import { RatingTrendsChart } from '../components/charts/RatingTrendsChart';

/**
 * Agent Detail Page component.
 * Displays statistics and game history for a specific agent.
 */
export function AgentDetail() {
  const { t } = useTranslation();
  const params = useParams();
  const name = params['*'] ? decodeURIComponent(params['*']) : undefined;
  const navigate = useNavigate();
  const [agent, setAgent] = useState<AgentDetailResponse | null>(null);
  const [agentAnalytics, setAgentAnalytics] = useState<AgentPuzzleOutcomeResponse[]>([]);
  const [ratingHistory, setRatingHistory] = useState<BenchmarkDataResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Pagination & Filtering state
  const [filter, setFilter] = useState<'ALL' | 'SUCCESS' | 'FAILED'>('ALL');
  const [puzzleTypeFilter, setPuzzleTypeFilter] = useState<string>('ALL');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 15;

  useEffect(() => {
    const fetchData = async () => {
      if (!name) return;
      try {
        setLoading(true);

        // Fetch agent detail, agent-specific analytics, and global analytics for trends
        const [agentData, analyticsData, globalAnalytics] = await Promise.all([
          api.getAgentDetail(name),
          api.getAgentAnalytics(name),
          api.getAnalytics(),
        ]);

        setAgent(agentData);
        setAgentAnalytics(analyticsData);

        // Filter global rating trends for this specific agent
        const filteredTrends = globalAnalytics.rating_trends.filter(
          (trend) => trend.agent_name.toLowerCase() === name.toLowerCase()
        );
        setRatingHistory(filteredTrends);
      } catch (err) {
        setError(t('common.error') + ': Failed to fetch agent details');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [name, t]);

  // Derived state for filtered games
  const { filteredGames, successRate, uniquePuzzleTypes } = useMemo(() => {
    if (!agent) return { filteredGames: [], successRate: 0, uniquePuzzleTypes: [] };

    // Calculate stats on the full dataset
    const wins = agent.games.filter((g) => !g.failed).length;
    const rate = (wins / agent.games.length) * 100;

    // Extract unique puzzle types
    const types = Array.from(new Set(agent.games.map((g) => g.puzzle_type).filter(Boolean))).sort();

    const filtered = agent.games.filter((game) => {
      const statusMatch =
        filter === 'ALL' ||
        (filter === 'SUCCESS' && !game.failed) ||
        (filter === 'FAILED' && game.failed);

      const typeMatch = puzzleTypeFilter === 'ALL' || game.puzzle_type === puzzleTypeFilter;

      return statusMatch && typeMatch;
    });

    // Sort by date descending (newest first)
    filtered.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());

    return { filteredGames: filtered, successRate: rate, uniquePuzzleTypes: types };
  }, [agent, filter, puzzleTypeFilter]);

  const totalPages = Math.ceil(filteredGames.length / pageSize);
  const currentGames = filteredGames.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const handleFilterChange = (newFilter: 'ALL' | 'SUCCESS' | 'FAILED') => {
    setFilter(newFilter);
    setCurrentPage(1);
  };

  if (loading) {
    return <AgentDetailSkeleton />;
  }

  if (error || !agent) {
    return (
      <div className="agent-error-state">
        <div className="card error-card">
          <Activity className="error-icon" />
          <h2>{t('common.error')}</h2>
          <p>{error || 'Agent not found'}</p>
          <Link to="/leaderboard" className="btn btn-secondary">
            <ArrowLeft size={16} /> {t('agentDetail.backToLeaderboard')}
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="agent-detail-page animate-fade-in">
      {/* Navigation */}
      <div className="nav-breadcrumb">
        <Link to="/leaderboard" className="breadcrumb-link">
          <ArrowLeft size={16} />
          <span>{t('agentDetail.backToLeaderboard')}</span>
        </Link>
      </div>

      {/* Hero Header */}
      <div className="agent-hero">
        <div className="agent-hero-content">
          <div className="agent-info">
            <h1 className="agent-name">{agent.name}</h1>
            <div className="agent-badges">
              {agent.is_reasoning && (
                <span className="badge badge-info">
                  <Brain size={12} /> {t('agentDetail.isReasoning')}
                </span>
              )}
              {agent.is_random && (
                <span className="badge badge-warning">
                  <Dice5 size={12} /> {t('agentDetail.isRandom')}
                </span>
              )}
              <span className="badge badge-neutral">v1.0.0</span>
            </div>
          </div>

          <div className="agent-hero-stats">
            <div className="hero-stat-label">{t('agentDetail.rating')}</div>
            <div className="hero-stat-value">{Math.round(agent.rating)}</div>
            <div className="hero-stat-sub">±{Math.round(agent.rd)} RD</div>
          </div>
        </div>
        <div className="hero-glow-blue" />
        <div className="hero-glow-purple" />
      </div>

      {/* Stats Grid */}
      <div className="stats-grid">
        <StatCard
          icon={<Trophy size={20} className="text-yellow" />}
          label={t('agentDetail.rating')}
          value={`${Math.round(agent.rating)}`}
          subValue="Glicko-2"
          color="yellow"
        />
        <StatCard
          icon={<Activity size={20} className="text-emerald" />}
          label={t('agentDetail.winRate')}
          value={`${successRate.toFixed(1)}%`}
          subValue={`${agent.games.filter((g) => !g.failed).length} wins`}
          color="emerald"
        />
        <StatCard
          icon={<Gamepad2 size={20} className="text-blue" />}
          label={t('agentDetail.gamesPlayed')}
          value={agent.games.length.toLocaleString()}
          subValue="Puzzle attempts"
          color="blue"
        />
        <StatCard
          icon={<Activity size={20} className="text-purple" />}
          label="Volatility"
          value={agent.volatility.toFixed(3)}
          subValue="Rating stability"
          color="purple"
        />
      </div>

      {/* Performance Charts */}
      <div
        className="grid"
        style={{
          gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
          gap: '2rem',
          marginBottom: '2rem',
        }}
      >
        <ChartCard
          title={t('agentDetail.performanceBreakdown')}
          description="Performance breakdown across different tactical themes"
          icon={<PieChart size={20} />}
        >
          <PuzzleOutcomesChart
            data={agentAnalytics.map((d) => ({
              type: d.type,
              successes: d.successes,
              failures: d.failures,
            }))}
          />
        </ChartCard>

        {ratingHistory.length > 0 && (
          <ChartCard
            title={t('analytics.charts.ratingTrends.title')}
            description="Progression of Glicko-2 rating over time"
            icon={<TrendingUp size={20} />}
          >
            <RatingTrendsChart data={ratingHistory} showConfidence />
          </ChartCard>
        )}
      </div>

      {/* Games Section */}

      <div className="card games-section">
        <div className="games-header">
          <div className="games-title-group">
            <h3>{t('agentDetail.gameHistory')}</h3>
            <span className="count-badge">{filteredGames.length}</span>
          </div>

          <div className="filter-group">
            <div className="filter-type-select-wrapper">
              <select
                className="filter-select"
                value={puzzleTypeFilter}
                onChange={(e) => {
                  setPuzzleTypeFilter(e.target.value);
                  setCurrentPage(1);
                }}
                aria-label="Filter by puzzle type"
              >
                <option value="ALL">{t('agentDetail.filters.allTypes')}</option>
                {uniquePuzzleTypes.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </div>
            <div className="filter-divider" />
            <FilterBtn
              active={filter === 'ALL'}
              onClick={() => handleFilterChange('ALL')}
              label={t('agentDetail.filters.allOutcomes')}
            />
            <FilterBtn
              active={filter === 'SUCCESS'}
              onClick={() => handleFilterChange('SUCCESS')}
              label={t('agentDetail.filters.success')}
              icon={<Check size={12} />}
            />
            <FilterBtn
              active={filter === 'FAILED'}
              onClick={() => handleFilterChange('FAILED')}
              label={t('agentDetail.filters.failed')}
              icon={<X size={12} />}
            />
          </div>
        </div>

        <div className="table-container">
          <table className="games-table">
            <thead>
              <tr>
                <th className="col-result">{t('agentDetail.table.outcome')}</th>
                <th className="col-date">{t('agentDetail.table.date')}</th>
                <th className="col-type">{t('agentDetail.table.type')}</th>
                <th className="col-puzzle">{t('agentDetail.table.puzzle')}</th>
                <th className="col-moves">{t('agentDetail.table.moves')}</th>
              </tr>
            </thead>
            <tbody>
              {currentGames.length > 0 ? (
                currentGames.map((game, i) => (
                  <tr
                    key={game.id || i}
                    className="game-row cursor-pointer hover:bg-slate-800/50 transition-colors"
                    onClick={() => navigate(`/replay/${game.id}`)}
                  >
                    <td>
                      {game.failed ? (
                        <span className="status-badge status-failed">
                          <X size={12} strokeWidth={3} /> {t('agentDetail.filters.failed')}
                        </span>
                      ) : (
                        <span className="status-badge status-solved">
                          <Check size={12} strokeWidth={3} /> {t('agentDetail.filters.success')}
                        </span>
                      )}
                    </td>
                    <td className="date-cell">
                      {new Date(game.date).toLocaleDateString(undefined, {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric',
                      })}
                      <span className="time-sub">
                        {new Date(game.date).toLocaleTimeString(undefined, {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </td>
                    <td className="type-cell">
                      <span className="type-badge">{game.puzzle_type}</span>
                    </td>
                    <td className="puzzle-id">{game.puzzle_id}</td>
                    <td className="moves-cell">{game.move_count}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="empty-state">
                    <Hash className="empty-icon" />
                    <p>{t('common.noData')}</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="pagination">
            <span className="pagination-info">
              Showing {(currentPage - 1) * pageSize + 1} -{' '}
              {Math.min(currentPage * pageSize, filteredGames.length)} of {filteredGames.length}
            </span>
            <div className="pagination-controls">
              <button
                className="btn btn-sm btn-outline"
                disabled={currentPage === 1}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              >
                {t('agentDetail.pagination.previous')}
              </button>
              <button
                className="btn btn-sm btn-outline"
                disabled={currentPage === totalPages}
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              >
                {t('agentDetail.pagination.next')}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Button component for filtering games.
 * @param props Component properties
 * @param props.active Whether the filter is active
 * @param props.onClick Click handler
 * @param props.label Button text
 * @param props.icon Optional icon
 */
function FilterBtn({
  active,
  onClick,
  label,
  icon,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  icon?: React.ReactNode;
}) {
  return (
    <button onClick={onClick} className={`filter-btn ${active ? 'active' : ''}`}>
      {icon}
      {label}
    </button>
  );
}

/**
 * Component to display a single statistic.
 * @param props Component properties
 * @param props.icon Icon to display
 * @param props.label Label for the statistic
 * @param props.value Value of the statistic
 * @param props.subValue Optional secondary value
 * @param props.color Accent color theme
 */
function StatCard({
  icon,
  label,
  value,
  subValue,
  color = 'blue',
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  subValue?: string;
  color?: string;
}) {
  return (
    <div className={`card stat-card color-${color}`}>
      <div className="stat-header">
        <div className={`stat-icon-wrapper`}>{icon}</div>
        {subValue && <span className="stat-tag">Stat</span>}
      </div>
      <div className="stat-content">
        <div className="stat-label">{label}</div>
        <div className="stat-value">{value}</div>
        {subValue && <div className="stat-sub">{subValue}</div>}
      </div>
    </div>
  );
}

/**
 * Skeleton component for loading state.
 */
function AgentDetailSkeleton() {
  return (
    <div
      role="status"
      aria-label="Loading agent details"
      className="agent-detail-page skeleton-wrapper"
    >
      <span className="sr-only">Loading agent details...</span>
      <div className="skeleton skeleton-hero" />

      <div className="skeleton-grid">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="skeleton skeleton-card" />
        ))}
      </div>

      <div className="skeleton skeleton-table" />
    </div>
  );
}
