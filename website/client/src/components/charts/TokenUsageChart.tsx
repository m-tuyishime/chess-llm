import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions,
  ChartData,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';
import { TokenUsageResponse } from '../../api/types';

// Register Chart.js components
ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

interface TokenUsageChartProps {
  data: TokenUsageResponse[];
}

/**
 * Bar chart component showing the average prompt and completion token usage per move for each agent.
 * Uses TokenUsageResponse from the API.
 * @param props - Component props
 * @param props.data - The token usage data
 */
export const TokenUsageChart: React.FC<TokenUsageChartProps> = ({ data }) => {
  const labels = data.map((d) => d.agent_name);

  const chartData: ChartData<'bar'> = {
    labels,
    datasets: [
      {
        label: 'Avg Prompt Tokens',
        data: data.map((d) => d.avg_prompt_tokens),
        backgroundColor: '#3b82f6', // --accent-primary
        borderRadius: 4,
      },
      {
        label: 'Avg Completion Tokens',
        data: data.map((d) => d.avg_completion_tokens),
        backgroundColor: '#8b5cf6', // --accent-secondary
        borderRadius: 4,
      },
    ],
  };

  const options: ChartOptions<'bar'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          color: '#94a3b8',
          font: {
            family: "'Inter', sans-serif",
            size: 12,
          },
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
        beginAtZero: true,
        title: {
          display: true,
          text: 'Tokens per Move',
          color: '#94a3b8',
        },
      },
    },
  };

  return <Bar data={chartData} options={options} />;
};
