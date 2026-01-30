import React from 'react';
import {
  Chart as ChartJS,
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
ChartJS.register(LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

interface RatingDeviationChartProps {
  data: BenchmarkDataResponse[];
}

/**
 * Line chart component showing the rating deviation (RD) trends of agents.
 * As more games are played, the RD should decrease, indicating higher certainty.
 * @param props - Component props
 * @param props.data - The benchmark data containing RD
 */
export const RatingDeviationChart: React.FC<RatingDeviationChartProps> = ({ data }) => {
  // Group data by agent
  const agents = Array.from(new Set(data.map((d) => d.agent_name)));

  // Generate datasets for each agent
  const datasets = agents.map((agent, index) => {
    const agentData = data
      .filter((d) => d.agent_name === agent)
      .sort((a, b) => a.evaluation_index - b.evaluation_index);

    // Map agent data to { x, y } points (index, deviation)
    const dataPoints = agentData.map((d) => ({
      x: d.evaluation_index,
      y: d.agent_deviation,
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

    return {
      label: agent,
      data: dataPoints,
      borderColor: color,
      backgroundColor: color + '33',
      borderWidth: 2,
      pointRadius: 0,
      pointHoverRadius: 5,
      tension: 0.1, // Less tension for RD as it's usually a smoother decline
      spanGaps: true,
    };
  });

  const chartData: ChartData<'line'> = {
    datasets,
  };

  const options: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
      axis: 'x',
    },
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          color: '#94a3b8',
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
          label: (context) => {
            const val = context.parsed.y !== null ? Math.round(context.parsed.y as number) : 0;
            return ` ${context.dataset.label}: ±${val} RD`;
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
        beginAtZero: true,
        grid: {
          color: 'rgba(148, 163, 184, 0.1)',
        },
        ticks: {
          color: '#94a3b8',
        },
        title: {
          display: true,
          text: 'Rating Deviation (RD)',
          color: '#94a3b8',
          font: {
            size: 11,
          },
        },
      },
    },
  };

  return <Line data={chartData} options={options} />;
};
