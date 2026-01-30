import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { AnalyticsResponse } from '../api/types';
import { ChartCard } from '../components/ChartCard';
import { RatingTrendsChart } from '../components/charts/RatingTrendsChart';
import { RatingDeviationChart } from '../components/charts/RatingDeviationChart';
import { FinalRatingsIntervalsChart } from '../components/charts/FinalRatingsIntervalsChart';
import { IllegalMovesChart } from '../components/charts/IllegalMovesChart';

import { PuzzleOutcomesChart } from '../components/charts/PuzzleOutcomesChart';
import { TokenUsageChart } from '../components/charts/TokenUsageChart';
import { AlertTriangle, PieChart, Zap, TrendingUp, Activity, Target } from 'lucide-react';

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
    <div
      className="container animate-fade-in"
      style={{ paddingTop: '2rem', paddingBottom: '5rem' }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '3rem' }}>
        <ChartCard
          title="Model Rating Trends"
          description="Glicko-2 rating evolution across evaluation periods"
          icon={<TrendingUp size={20} />}
        >
          <RatingTrendsChart data={data.rating_trends} />
        </ChartCard>

        <ChartCard
          title="Rating Deviation Trends"
          description="Confidence intervals (RD) decreasing as models solve more puzzles"
          icon={<Activity size={20} />}
        >
          <RatingDeviationChart data={data.rating_trends} />
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

        <ChartCard
          title="Final Rating Confidence Intervals"
          description="95% confidence intervals (±2 RD) compared against the benchmark puzzle difficulty (green band)"
          icon={<Target size={20} />}
          minHeight="600px"
        >
          <FinalRatingsIntervalsChart
            data={data.final_ratings}
            weightedRating={data.weighted_puzzle_rating}
            weightedDeviation={data.weighted_puzzle_deviation}
          />
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
    <div className="container" style={{ paddingTop: '2rem', paddingBottom: '5rem' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '3rem' }}>
        {[...Array(6)].map((_, i) => (
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
