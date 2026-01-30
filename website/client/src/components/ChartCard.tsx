import React from 'react';

interface ChartCardProps {
  title: string;
  description?: string;
  children: React.ReactNode;
  icon?: React.ReactNode;
  minHeight?: string;
}

/**
 * A wrapper component for charts that provides a consistent layout,
 * including a title, optional description, and icon.
 * @param props - Component props
 * @param props.title - The title
 * @param props.description - Optional description
 * @param props.children - The chart content
 * @param props.icon - Optional icon
 * @param props.minHeight - Minimum height for the chart container
 */
export function ChartCard({
  title,
  description,
  children,
  icon,
  minHeight = '300px',
}: ChartCardProps) {
  return (
    <div
      className="card animate-fade-in"
      style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
    >
      <div className="stat-header" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {icon && <div className="stat-icon-wrapper color-blue">{icon}</div>}
          <div>
            <h3 style={{ margin: 0, fontSize: '1.125rem', fontWeight: 700 }}>{title}</h3>
            {description && (
              <p
                style={{
                  margin: '0.25rem 0 0 0',
                  fontSize: '0.875rem',
                  color: 'var(--text-secondary)',
                }}
              >
                {description}
              </p>
            )}
          </div>
        </div>
      </div>
      <div style={{ flex: 1, minHeight, position: 'relative' }}>{children}</div>
    </div>
  );
}
