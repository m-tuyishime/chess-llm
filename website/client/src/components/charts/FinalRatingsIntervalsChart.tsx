import React, { useMemo } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ScatterController,
  Title,
  Tooltip,
  Legend,
  Filler,
  Plugin,
  ChartData,
  ChartOptions,
} from 'chart.js';
import { Chart } from 'react-chartjs-2';
import { RatingIntervalResponse } from '../../api/types';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ScatterController,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface FinalRatingsIntervalsChartProps {
  data: RatingIntervalResponse[];
  weightedRating: number | null;
  weightedDeviation: number | null;
}

/**
 * Chart component showing final agent ratings with 95% confidence intervals.
 * Also displays the weighted puzzle rating spread as a reference.
 * @param props - Component props
 * @param props.data - Final ratings and deviations for each agent
 * @param props.weightedRating - Reference puzzle rating
 * @param props.weightedDeviation - Reference puzzle deviation
 */
export const FinalRatingsIntervalsChart: React.FC<FinalRatingsIntervalsChartProps> = ({
  data,
  weightedRating,
  weightedDeviation,
}) => {
  // Sort data by rating descending
  const sortedData = useMemo(
    () => [...data].sort((a, b) => b.agent_rating - a.agent_rating),
    [data]
  );
  const labels = useMemo(() => sortedData.map((d) => d.agent_name), [sortedData]);

  // Calculate Y-axis range to include all error bars and the benchmark spread
  const yRange = useMemo(() => {
    if (sortedData.length === 0) return { min: 0, max: 2000 };

    let min = Math.min(...sortedData.map((d) => d.agent_rating - d.error));
    let max = Math.max(...sortedData.map((d) => d.agent_rating + d.error));

    if (weightedRating !== null && weightedDeviation !== null) {
      const puzzleError = weightedDeviation * 2;
      min = Math.min(min, weightedRating - puzzleError);
      max = Math.max(max, weightedRating + puzzleError);
    }

    // Add 10% padding
    const padding = (max - min) * 0.1;
    return {
      min: Math.floor((min - padding) / 100) * 100,
      max: Math.ceil((max + padding) / 100) * 100,
    };
  }, [sortedData, weightedRating, weightedDeviation]);

  /**
   * Custom plugin to draw error bars (vertical lines with caps).
   * This mimics the look of Matplotlib's errorbar function.
   */
  const errorBarsPlugin: Plugin<'line' | 'bar' | 'scatter'> = {
    id: 'errorBars',
    afterDatasetsDraw: (chart) => {
      const {
        ctx,
        scales: { x, y },
      } = chart;

      // Find the model rating dataset
      const datasetIndex = chart.data.datasets.findIndex((ds) => ds.label === 'Model Final Rating');
      if (datasetIndex === -1) return;

      ctx.save();
      ctx.strokeStyle = '#ef4444'; // Red for error bars
      ctx.lineWidth = 3; // Thicker error bars

      sortedData.forEach((item, index) => {
        const xPixel = x.getPixelForTick(index);
        const yTop = y.getPixelForValue(item.agent_rating + item.error);
        const yBottom = y.getPixelForValue(item.agent_rating - item.error);

        // Draw vertical line
        ctx.beginPath();
        ctx.moveTo(xPixel, yTop);
        ctx.lineTo(xPixel, yBottom);
        ctx.stroke();

        // Draw horizontal caps
        const capWidth = 10; // Wider caps
        ctx.beginPath();
        ctx.moveTo(xPixel - capWidth, yTop);
        ctx.lineTo(xPixel + capWidth, yTop);
        ctx.moveTo(xPixel - capWidth, yBottom);
        ctx.lineTo(xPixel + capWidth, yBottom);
        ctx.stroke();
      });
      ctx.restore();
    },
  };

  /**
   * Custom plugin to draw the weighted puzzle rating background band.
   */
  const puzzleSpreadPlugin: Plugin<'line' | 'bar' | 'scatter'> = {
    id: 'puzzleSpread',
    beforeDatasetsDraw: (chart) => {
      if (weightedRating === null || weightedDeviation === null) return;
      const {
        ctx,
        chartArea: { left, right },
        scales: { y },
      } = chart;

      const puzzleError = weightedDeviation * 2;
      const yTop = y.getPixelForValue(weightedRating + puzzleError);
      const yBottom = y.getPixelForValue(weightedRating - puzzleError);
      const yMid = y.getPixelForValue(weightedRating);

      ctx.save();
      // Draw spread band
      ctx.fillStyle = 'rgba(16, 185, 129, 0.15)'; // Slightly darker green
      ctx.fillRect(left, yTop, right - left, yBottom - yTop);

      // Draw dashed midline
      ctx.strokeStyle = 'rgba(16, 185, 129, 0.6)';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([5, 5]);
      ctx.beginPath();
      ctx.moveTo(left, yMid);
      ctx.lineTo(right, yMid);
      ctx.stroke();
      ctx.restore();
    },
  };

  const chartData: ChartData = {
    labels,
    datasets: [
      {
        type: 'scatter' as const,
        label: 'Model Final Rating',
        data: sortedData.map((d, i) => ({ x: i, y: d.agent_rating })),
        backgroundColor: '#3b82f6',
        borderColor: '#2563eb',
        borderWidth: 1,
        pointRadius: 8,
        pointHoverRadius: 10,
      },
      // Legend proxies
      {
        type: 'line' as const,
        label: '95% Confidence Interval (±2 RD)',
        data: [],
        borderColor: '#ef4444',
        backgroundColor: '#ef4444',
        borderWidth: 2,
      },
      {
        type: 'line' as const,
        label: 'Benchmark Puzzle Difficulty (Avg)',
        data: [],
        backgroundColor: 'rgba(16, 185, 129, 0.2)',
        borderColor: 'rgba(16, 185, 129, 0.6)',
        borderDash: [5, 5],
        fill: true,
      },
    ],
  };

  const options: ChartOptions = useMemo(
    () => ({
      responsive: true,
      maintainAspectRatio: false,
      layout: {
        padding: {
          top: 20,
          bottom: 40, // More bottom padding for slanted labels
        },
      },
      interaction: {
        mode: 'nearest',
        axis: 'x',
        intersect: false,
      },
      animation: false,
      plugins: {
        legend: {
          position: 'top' as const,
          labels: {
            color: '#94a3b8',
            font: { family: "'Inter', sans-serif", size: 11 },
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
            label: (context) => {
              const item = sortedData[context.dataIndex];
              if (context.dataset.label === 'Model Final Rating') {
                return ` Rating: ${Math.round(item.agent_rating)} (±${Math.round(
                  item.agent_deviation
                )} RD)`;
              }
              return '';
            },
          },
        },
      },
      scales: {
        x: {
          type: 'category',
          grid: { display: false },
          ticks: {
            color: '#94a3b8',
            autoSkip: false,
            maxRotation: 45,
            minRotation: 45,
            font: { size: 10 },
          },
        },
        y: {
          type: 'linear' as const,
          min: yRange.min,
          max: yRange.max,
          grid: { color: 'rgba(148, 163, 184, 0.1)' },
          ticks: { color: '#94a3b8', maxTicksLimit: 10, stepSize: 100 },
          title: {
            display: true,
            text: 'Glicko-2 Rating',
            color: '#94a3b8',
            font: { size: 11, weight: 'bold' },
          },
        },
      },
    }),
    [yRange, sortedData]
  );

  return (
    <Chart
      type="scatter"
      data={chartData}
      options={options}
      plugins={[errorBarsPlugin, puzzleSpreadPlugin]}
    />
  );
};
