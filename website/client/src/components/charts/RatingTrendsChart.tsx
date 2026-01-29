import React from 'react';
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
}

/**
 * Line chart component showing the rating trends of agents over time.
 * Uses BenchmarkDataResponse from the API.
 * @param props - Component props
 * @param props.data - The rating trends data
 */
export const RatingTrendsChart: React.FC<RatingTrendsChartProps> = ({ data }) => {
  // Sort data by date
  const sortedData = [...data].sort(
    (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
  );

  // Group data by agent
  const agents = Array.from(new Set(sortedData.map((d) => d.agent_name)));

  // Extract unique dates for labels
  const labels = Array.from(
    new Set(
      sortedData.map((d) => {
        const date = new Date(d.date);
        return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
      })
    )
  );

  // Generate datasets for each agent
  const datasets = agents.map((agent, index) => {
    const agentData = sortedData.filter((d) => d.agent_name === agent);

    // Map agent data to the labels (dates)
    // If an agent doesn't have data for a specific date, it will be null
    const dataPoints = labels.map((label) => {
      const match = agentData.find((d) => {
        const dDate = new Date(d.date).toLocaleDateString(undefined, {
          month: 'short',
          day: 'numeric',
        });
        return dDate === label;
      });
      return match ? match.agent_rating : null;
    });

    // Cycle through some nice colors
    const colors = [
      '#3b82f6', // Blue
      '#8b5cf6', // Violet
      '#ec4899', // Pink
      '#10b981', // Emerald
      '#f59e0b', // Amber
    ];
    const color = colors[index % colors.length];

    return {
      label: agent,
      data: dataPoints,
      borderColor: color,
      backgroundColor: color + '33', // 20% opacity
      tension: 0.3,
      pointRadius: 4,
      pointHoverRadius: 6,
      spanGaps: true, // Connect lines even if data is missing for some dates
    };
  });

  const chartData: ChartData<'line'> = {
    labels,
    datasets,
  };

  const options: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          color: '#94a3b8', // --text-secondary
          font: {
            family: "'Inter', sans-serif",
            size: 12,
          },
          usePointStyle: true,
          padding: 20,
        },
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        backgroundColor: '#1e293b',
        titleColor: '#f8fafc',
        bodyColor: '#f8fafc',
        borderColor: '#334155',
        borderWidth: 1,
        padding: 12,
        cornerRadius: 8,
      },
    },
    scales: {
      x: {
        grid: {
          display: false,
        },
        ticks: {
          color: '#94a3b8',
        },
      },
      y: {
        grid: {
          color: 'rgba(148, 163, 184, 0.1)',
        },
        ticks: {
          color: '#94a3b8',
        },
        title: {
          display: true,
          text: 'Glicko-2 Rating',
          color: '#94a3b8',
        },
      },
    },
  };

  return <Line data={chartData} options={options} />;
};
