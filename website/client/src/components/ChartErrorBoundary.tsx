import React from 'react';

interface ChartErrorBoundaryProps {
  children: React.ReactNode;
  title: string;
}

interface ChartErrorBoundaryState {
  hasError: boolean;
}

/**
 * Error boundary to prevent a single chart failure from blanking the analytics page.
 */
export class ChartErrorBoundary extends React.Component<
  ChartErrorBoundaryProps,
  ChartErrorBoundaryState
> {
  state: ChartErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ChartErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: unknown): void {
    console.error(`Chart failed to render: ${this.props.title}`, error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          className="card"
          style={{
            padding: '1.5rem',
            border: '1px solid var(--border-color)',
            color: 'var(--text-secondary)',
            textAlign: 'center',
          }}
        >
          <strong>{this.props.title}</strong>
          <div style={{ marginTop: '0.5rem' }}>
            Chart failed to render. Check the browser console for details.
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
