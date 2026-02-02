import React, { useMemo } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions,
  ChartData,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { BenchmarkDataResponse } from '../../api/types';

// Register Chart.js components
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

interface RatingTrendsChartProps {
  data: BenchmarkDataResponse[];
  showConfidence?: boolean;
}

/**
 * Line chart component showing the rating trends of agents over time.
 * Uses BenchmarkDataResponse from the API.
 * @param props - Component props
 * @param props.data - The rating trends data
 * @param props.showConfidence - Whether to render a confidence band around the line
 */
export const RatingTrendsChart: React.FC<RatingTrendsChartProps> = ({
  data,
  showConfidence = false,
}) => {
  const toRgba = (hex: string, alpha: number) => {
    const normalized = hex.replace('#', '');
    const bigint = parseInt(normalized, 16);
    const r = (bigint >> 16) & 255;
    const g = (bigint >> 8) & 255;
    const b = bigint & 255;
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  };

  // Memoize datasets calculation to avoid heavy lifting on every render
  const datasets = useMemo(() => {
    // Group data by agent
    const agents = Array.from(new Set(data.map((d) => d.agent_name)));

    return agents.flatMap((agent, index) => {
      const agentData = data
        .filter((d) => d.agent_name === agent)
        .sort((a, b) => a.evaluation_index - b.evaluation_index);

      // Map agent data to { x, y } points for linear scale
      const dataPoints = agentData.map((d) => ({
        x: d.evaluation_index,
        y: d.agent_rating,
      }));

      // Cycle through a larger palette of high-contrast distinct colors
      const colors = [
        '#3b82f6', // Blue
        '#ef4444', // Red
        '#10b981', // Emerald
        '#f59e0b', // Amber
        '#8b5cf6', // Violet
        '#ec4899', // Pink
        '#06b6d4', // Cyan
        '#f97316', // Orange
        '#84cc16', // Lime
        '#a855f7', // Purple
        '#14b8a6', // Teal
        '#fb7185', // Rose
      ];
      const color = colors[index % colors.length];

      if (showConfidence) {
        const lowerBand = agentData.map((d) => ({
          x: d.evaluation_index,
          y: d.agent_rating - d.agent_deviation * 2,
        }));
        const upperBand = agentData.map((d) => ({
          x: d.evaluation_index,
          y: d.agent_rating + d.agent_deviation * 2,
        }));

        return [
          {
            label: `${agent} confidence lower`,
            data: lowerBand,
            borderColor: 'transparent',
            backgroundColor: 'transparent',
            pointRadius: 0,
            tension: 0.3,
            fill: false,
          },
          {
            label: `${agent} confidence`,
            data: upperBand,
            borderColor: 'transparent',
            backgroundColor: toRgba(color, 0.12),
            pointRadius: 0,
            tension: 0.3,
            fill: '-1',
          },
          {
            label: agent,
            data: dataPoints,
            borderColor: color,
            backgroundColor: color + '33', // 20% opacity
            tension: 0.3,
            borderWidth: 2,
            pointRadius: 0, // Hide points by default for performance and clarity
            pointHoverRadius: 5, // Show point on hover
            spanGaps: true,
          },
        ];
      }

      return {
        label: agent,
        data: dataPoints,
        borderColor: color,
        backgroundColor: color + '33', // 20% opacity
        tension: 0.3,
        borderWidth: 2,
        pointRadius: 0, // Hide points by default for performance and clarity
        pointHoverRadius: 5, // Show point on hover
        spanGaps: true,
      };
    });
  }, [data, showConfidence]);

  const chartData: ChartData<'line'> = {
    datasets,
  };

  const options: ChartOptions<'line'> = useMemo(
    () => ({
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false,
        axis: 'x',
      },
      animation: false, // Disable animations for faster initial load
      plugins: {
        legend: {
          position: 'top' as const,
          labels: {
            color: '#94a3b8', // --text-secondary
            font: {
              family: "'Inter', sans-serif",
              size: 11,
            },
            usePointStyle: true,
            padding: 15,
          },
        },
        tooltip: {
          backgroundColor: '#1e293b',
          titleColor: '#f8fafc',
          bodyColor: '#f8fafc',
          borderColor: '#334155',
          borderWidth: 1,
          padding: 12,
          cornerRadius: 8,
          callbacks: {
            title: (tooltipItems) => {
              const index = tooltipItems[0].parsed.x;
              return `Evaluation #${index}`;
            },
          },
        },
      },
      scales: {
        x: {
          type: 'linear' as const,
          grid: {
            display: false,
          },
          ticks: {
            color: '#94a3b8',
            maxTicksLimit: 10,
            precision: 0,
          },
          title: {
            display: true,
            text: 'Evaluation Index',
            color: '#94a3b8',
            font: {
              size: 11,
            },
          },
        },
        y: {
          type: 'linear' as const,
          grid: {
            color: 'rgba(148, 163, 184, 0.1)',
          },
          ticks: {
            color: '#94a3b8',
            maxTicksLimit: 10,
            stepSize: 100, // IMPORTANT: Prevent tick explosion
          },
          title: {
            display: true,
            text: 'Glicko-2 Rating',
            color: '#94a3b8',
            font: {
              size: 11,
            },
          },
        },
      },
    }),
    []
  );

  return <Line data={chartData} options={options} />;
};
