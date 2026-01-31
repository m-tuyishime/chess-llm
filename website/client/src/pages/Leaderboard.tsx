// React import removed as handled by JSX transform

/**
 * Leaderboard Page component.
 * Displays the ranking of agents.
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { api } from '../api/client';
import { AgentRankingResponse } from '../api/types';

/**
 * Leaderboard Page component.
 * Displays the ranking of agents via a table.
 */
export function Leaderboard() {
  const { t } = useTranslation();
  const [rankings, setRankings] = useState<AgentRankingResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchLeaderboard = async () => {
      try {
        const data = await api.getLeaderboard();
        setRankings(data);
      } catch (err) {
        setError(t('common.error') + ': Failed to fetch leaderboard');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchLeaderboard();
  }, [t]);

  if (loading) {
    return (
      <div className="agent-detail-page">
        <div className="skeleton skeleton-hero" style={{ height: '100px' }}></div>
        <div className="skeleton skeleton-table"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="card"
        style={{ textAlign: 'center', borderColor: 'var(--status-failed-text)' }}
      >
        <p style={{ color: 'var(--status-failed-text)' }}>{error}</p>
      </div>
    );
  }

  return (
    <div className="agent-detail-page">
      <div className="flex justify-between items-end">
        <div>
          <h1>{t('leaderboard.title')}</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '1.1rem' }}>
            {t('leaderboard.subtitle')}
          </p>
        </div>
        <div className="badge badge-neutral" style={{ padding: '0.5rem 1rem', fontSize: '0.9rem' }}>
          {t('leaderboard.activeAgents', { count: rankings.length })}
        </div>
      </div>

      <div className="games-section">
        <div className="table-container">
          <table className="games-table">
            <thead>
              <tr>
                <th style={{ width: '80px', textAlign: 'center' }}>
                  {t('leaderboard.table.rank')}
                </th>
                <th>{t('leaderboard.table.model')}</th>
                <th style={{ textAlign: 'right' }}>{t('leaderboard.table.rating')}</th>
                <th style={{ textAlign: 'right' }}>{t('leaderboard.table.rd')}</th>
                <th style={{ width: '200px' }}>{t('leaderboard.table.winRate')}</th>
                <th style={{ textAlign: 'right' }}>{t('leaderboard.table.games')}</th>
              </tr>
            </thead>
            <tbody>
              {rankings.map((agent, index) => {
                const rank = index + 1;
                let rankBadgeClass = '';
                if (rank === 1) rankBadgeClass = 'rank-1';
                else if (rank === 2) rankBadgeClass = 'rank-2';
                else if (rank === 3) rankBadgeClass = 'rank-3';

                return (
                  <tr
                    key={agent.name}
                    className="game-row"
                    onClick={() => navigate(`/agent/${encodeURIComponent(agent.name)}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td style={{ textAlign: 'center' }}>
                      {rank <= 3 ? (
                        <span className={`rank-badge ${rankBadgeClass}`}>{rank}</span>
                      ) : (
                        <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>
                          #{rank}
                        </span>
                      )}
                    </td>
                    <td>
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                        {agent.name}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                        {t('leaderboard.table.rating')}: {Math.round(agent.rating)}
                      </div>
                    </td>
                    <td
                      style={{
                        textAlign: 'right',
                        fontFamily: 'monospace',
                        fontWeight: 700,
                        fontSize: '1.1rem',
                      }}
                    >
                      {Math.round(agent.rating)}
                    </td>
                    <td style={{ textAlign: 'right', color: 'var(--text-secondary)' }}>
                      ±{Math.round(agent.rd)}
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        <div className="win-rate-bar-bg">
                          <div
                            className="win-rate-bar-fill"
                            style={{ width: `${agent.win_rate * 100}%` }}
                          />
                        </div>
                        <span style={{ fontFamily: 'monospace', color: 'var(--text-primary)' }}>
                          {(agent.win_rate * 100).toFixed(1)}%
                        </span>
                      </div>
                    </td>
                    <td
                      style={{
                        textAlign: 'right',
                        fontFamily: 'monospace',
                        color: 'var(--text-secondary)',
                      }}
                    >
                      {agent.games_played}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
