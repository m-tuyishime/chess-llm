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
import { IllegalMoveResponse } from '../../api/types';

// Register Chart.js components
ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

interface IllegalMovesChartProps {
  data: IllegalMoveResponse[];
}

/**
 * Bar chart component showing the percentage of illegal moves attempted by each agent.
 * Uses IllegalMoveResponse from the API.
 * @param props - Component props
 * @param props.data - The illegal moves data
 */
export const IllegalMovesChart: React.FC<IllegalMovesChartProps> = ({ data }) => {
  // Sort by percentage descending
  const sortedData = [...data].sort((a, b) => b.illegal_percentage - a.illegal_percentage);

  const labels = sortedData.map((d) => d.agent_name);

  const chartData: ChartData<'bar'> = {
    labels,
    datasets: [
      {
        label: 'Illegal Move %',
        data: sortedData.map((d) => d.illegal_percentage),
        backgroundColor: (context) => {
          // Color bars based on percentage
          const val = context.raw as number;
          if (val > 20) return '#ef4444'; // Red for high illegal rate
          if (val > 5) return '#f59e0b'; // Amber for medium
          return '#3b82f6'; // Blue for low
        },
        borderRadius: 6,
        borderWidth: 0,
      },
    ],
  };

  const options: ChartOptions<'bar'> = {
    indexAxis: 'y' as const, // Horizontal bar chart
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false, // Only one dataset, legend not needed
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
          label: (context) => {
            const item = sortedData[context.dataIndex];
            const val = context.parsed.x !== null ? context.parsed.x.toFixed(1) : '0';
            return ` ${val}% (${item.illegal_moves_count}/${item.total_moves} moves)`;
          },
        },
      },
    },
    scales: {
      x: {
        grid: {
          color: 'rgba(148, 163, 184, 0.1)',
        },
        ticks: {
          color: '#94a3b8',
          callback: (value) => `${value}%`,
        },
        beginAtZero: true,
        max: 100,
        title: {
          display: true,
          text: 'Illegal Move Rate (%)',
          color: '#94a3b8',
        },
      },
      y: {
        grid: {
          display: false,
        },
        ticks: {
          color: '#94a3b8',
        },
      },
    },
  };

  return <Bar data={chartData} options={options} />;
};
