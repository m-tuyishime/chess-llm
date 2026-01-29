import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { AnalyticsResponse } from '../api/types';
import { ChartCard } from '../components/ChartCard';
import { RatingTrendsChart } from '../components/charts/RatingTrendsChart';
import { IllegalMovesChart } from '../components/charts/IllegalMovesChart';
import { PuzzleOutcomesChart } from '../components/charts/PuzzleOutcomesChart';
import { TokenUsageChart } from '../components/charts/TokenUsageChart';
import { AlertTriangle, PieChart, Zap, TrendingUp } from 'lucide-react';

/**
 * Analytics page component.
 * Displays interactive charts and model performance comparisons.
 */
export function Analytics() {
  const [data, setData] = useState<AnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setLoading(true);
        const analyticsData = await api.getAnalytics();
        setData(analyticsData);
      } catch (err) {
        console.error('Failed to fetch analytics:', err);
        setError('Failed to load analytics data. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    fetchAnalytics();
  }, []);

  if (loading) {
    return <AnalyticsSkeleton />;
  }

  if (error || !data) {
    return (
      <div className="container">
        <div
          className="card error-card"
          style={{ textAlign: 'center', padding: '3rem', marginTop: '2rem' }}
        >
          <AlertTriangle
            size={48}
            style={{ color: 'var(--status-failed-text)', marginBottom: '1rem' }}
          />
          <h2>Error</h2>
          <p>{error || 'An unexpected error occurred'}</p>
          <button
            className="btn btn-primary"
            onClick={() => window.location.reload()}
            style={{ marginTop: '1.5rem' }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="container animate-fade-in">
      <header style={{ marginBottom: '2rem' }}>
        <h1>Analytics & Comparison</h1>
        <p style={{ color: 'var(--text-secondary)' }}>
          Detailed performance metrics and rating trends for all agents.
        </p>
      </header>

      <div
        className="grid"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(450px, 1fr))', gap: '2rem' }}
      >
        <ChartCard
          title="Model Rating Trends"
          description="Glicko-2 rating evolution across evaluation periods"
          icon={<TrendingUp size={20} />}
        >
          <RatingTrendsChart data={data.rating_trends} />
        </ChartCard>

        <ChartCard
          title="Illegal Move Rate"
          description="Percentage of attempted moves that were invalid according to FIDE rules"
          icon={<AlertTriangle size={20} />}
        >
          <IllegalMovesChart data={data.illegal_moves} />
        </ChartCard>

        <ChartCard
          title="Overall Puzzle Outcomes"
          description="Success vs failure counts aggregated by puzzle theme"
          icon={<PieChart size={20} />}
        >
          <PuzzleOutcomesChart data={data.puzzle_outcomes} />
        </ChartCard>

        <ChartCard
          title="Token Efficiency"
          description="Average prompt and completion tokens used per move"
          icon={<Zap size={20} />}
        >
          <TokenUsageChart data={data.token_usage} />
        </ChartCard>
      </div>
    </div>
  );
}

/**
 * Skeleton loading component for Analytics page.
 */
function AnalyticsSkeleton() {
  return (
    <div className="container" style={{ paddingTop: '2rem' }}>
      <div className="skeleton" style={{ height: '3rem', width: '300px', marginBottom: '1rem' }} />
      <div
        className="skeleton"
        style={{ height: '1.5rem', width: '500px', marginBottom: '3rem' }}
      />

      <div
        className="grid"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(450px, 1fr))', gap: '2rem' }}
      >
        {[...Array(4)].map((_, i) => (
          <div
            key={i}
            className="skeleton"
            style={{ height: '400px', borderRadius: 'var(--radius-md)' }}
          />
        ))}
      </div>
    </div>
  );
}
