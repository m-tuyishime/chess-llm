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
import { PuzzleOutcomeResponse } from '../../api/types';

// Register Chart.js components
ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

interface PuzzleOutcomesChartProps {
  data: PuzzleOutcomeResponse[];
}

/**
 * Bar chart component showing successes vs failures for each puzzle type.
 * Uses PuzzleOutcomeResponse from the API.
 * @param props - Component props
 * @param props.data - The puzzle outcomes data
 */
export const PuzzleOutcomesChart: React.FC<PuzzleOutcomesChartProps> = ({ data }) => {
  const labels = data.map((d) => d.type);

  const chartData: ChartData<'bar'> = {
    labels,
    datasets: [
      {
        label: 'Successes',
        data: data.map((d) => d.successes),
        backgroundColor: '#10b981', // --status-success-text (#10b981 is Emerald 500)
        borderRadius: 4,
      },
      {
        label: 'Failures',
        data: data.map((d) => d.failures),
        backgroundColor: '#ef4444', // --status-failed-text (#ef4444 is Red 500)
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
          stepSize: 1, // Successes/Failures are integers
        },
        beginAtZero: true,
      },
    },
  };

  return <Bar data={chartData} options={options} />;
};
