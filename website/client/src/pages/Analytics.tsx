import React from 'react';

/**
 * Analytics page component.
 * Displays interactive charts and model performance comparisons.
 */
export function Analytics() {
  return (
    <div className="container">
      <header style={{ marginBottom: '2rem' }}>
        <h1>Analytics & Comparison</h1>
        <p style={{ color: 'var(--text-secondary)' }}>
          Detailed performance metrics and rating trends for all agents.
        </p>
      </header>

      <div
        className="grid"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '2rem' }}
      >
        <section className="card">
          <h2>Model Rating Trends</h2>
          <div
            style={{
              height: '300px',
              display: 'flex',
              alignItems: 'center',
              justifyItems: 'center',
              background: 'var(--bg-secondary)',
              borderRadius: '8px',
            }}
          >
            <p style={{ margin: 'auto', color: 'var(--text-secondary)' }}>
              Chart Placeholder: Line Chart
            </p>
          </div>
        </section>

        <section className="card">
          <h2>Percentage of Illegal Moves</h2>
          <div
            style={{
              height: '300px',
              display: 'flex',
              alignItems: 'center',
              justifyItems: 'center',
              background: 'var(--bg-secondary)',
              borderRadius: '8px',
            }}
          >
            <p style={{ margin: 'auto', color: 'var(--text-secondary)' }}>
              Chart Placeholder: Bar Chart
            </p>
          </div>
        </section>

        <section className="card">
          <h2>Puzzle Outcomes by Type</h2>
          <div
            style={{
              height: '300px',
              display: 'flex',
              alignItems: 'center',
              justifyItems: 'center',
              background: 'var(--bg-secondary)',
              borderRadius: '8px',
            }}
          >
            <p style={{ margin: 'auto', color: 'var(--text-secondary)' }}>
              Chart Placeholder: Radar/Pie Chart
            </p>
          </div>
        </section>

        <section className="card">
          <h2>Rating Deviation Trends</h2>
          <div
            style={{
              height: '300px',
              display: 'flex',
              alignItems: 'center',
              justifyItems: 'center',
              background: 'var(--bg-secondary)',
              borderRadius: '8px',
            }}
          >
            <p style={{ margin: 'auto', color: 'var(--text-secondary)' }}>
              Chart Placeholder: Line Chart
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
