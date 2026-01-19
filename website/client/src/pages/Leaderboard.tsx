// React import removed as handled by JSX transform

/**
 * Leaderboard Page component.
 * Displays the ranking of agents.
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { AgentRankingResponse } from '../api/types';

/**
 * Leaderboard Page component.
 * Displays the ranking of agents via a table.
 */
export function Leaderboard() {
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
        setError('Failed to fetch leaderboard');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchLeaderboard();
  }, []);

  if (loading) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: 'var(--spacing-lg)' }}>
        <p>Loading leaderboard...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="card"
        style={{ textAlign: 'center', padding: 'var(--spacing-lg)', borderColor: '#ef4444' }}
      >
        <p style={{ color: '#ef4444' }}>Error: {error}</p>
      </div>
    );
  }

  return (
    <div className="card">
      <div
        className="flex justify-between items-center"
        style={{ marginBottom: 'var(--spacing-sm)' }}
      >
        <h2>Leaderboard</h2>
        <span style={{ color: 'var(--text-secondary)' }}>{rankings.length} Agents</span>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table className="leaderboard-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Model</th>
              <th>Rating</th>
              <th>RD</th>
              <th>Win Rate</th>
              <th>Games</th>
            </tr>
          </thead>
          <tbody>
            {rankings.map((agent, index) => {
              const rank = index + 1;
              let rankBadgeClass = typeof rank === 'number' ? `rank-${rank}` : '';
              if (rank > 3) rankBadgeClass = '';

              return (
                <tr
                  key={agent.name}
                  onClick={() => navigate(`/agent/${agent.name}`)}
                  style={{ cursor: 'pointer', transition: 'background-color 0.2s' }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--glass-bg)')}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <td>
                    {rank <= 3 ? (
                      <span className={`rank-badge ${rankBadgeClass}`}>{rank}</span>
                    ) : (
                      <span
                        style={{
                          marginLeft: '0.5rem',
                          fontWeight: 'bold',
                          color: 'var(--text-secondary)',
                        }}
                      >
                        #{rank}
                      </span>
                    )}
                  </td>
                  <td style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{agent.name}</td>
                  <td style={{ fontFamily: 'monospace' }}>{Math.round(agent.rating)}</td>
                  <td style={{ color: 'var(--text-secondary)' }}>±{Math.round(agent.rd)}</td>
                  <td>
                    <div className="flex items-center gap-2">
                      <div
                        style={{
                          width: '60px',
                          height: '6px',
                          background: 'var(--bg-tertiary)',
                          borderRadius: '3px',
                          overflow: 'hidden',
                        }}
                      >
                        <div
                          style={{
                            width: `${agent.win_rate * 100}%`,
                            height: '100%',
                            background: 'var(--accent-gradient)',
                          }}
                        />
                      </div>
                      <span>{(agent.win_rate * 100).toFixed(1)}%</span>
                    </div>
                  </td>
                  <td>{agent.games_played}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
