import { useTranslation } from 'react-i18next';

/**
 * About Page component.
 * Displays information about the project based on the research report.
 */
export function About() {
  const { t } = useTranslation();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* Header Section */}
      <section style={{ textAlign: 'center', marginBottom: '1rem' }}>
        <h1
          style={{
            fontSize: '2.5rem',
            marginBottom: '0.5rem',
            background: 'var(--accent-gradient)',
            backgroundClip: 'text',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
        >
          {t('about.header.title')}
        </h1>
        <h2 style={{ fontSize: '1.25rem', color: 'var(--text-secondary)', fontWeight: '400' }}>
          {t('about.header.subtitle')}
        </h2>
        <p style={{ marginTop: '0.5rem', fontStyle: 'italic', color: 'var(--text-tertiary)' }}>
          {t('about.header.originalTitle')}
        </p>

        <div style={{ marginTop: '2rem' }}>
          <a
            href="/report.pdf"
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-primary"
            style={{ textDecoration: 'none' }}
          >
            📄 {t('about.header.readReport')}
          </a>
        </div>
      </section>

      {/* Abstract Section */}
      <div className="card">
        <h3>{t('about.abstract.title')}</h3>
        <p style={{ lineHeight: '1.6', color: 'var(--text-secondary)' }}>
          {t('about.abstract.p1')}
        </p>
        <p style={{ lineHeight: '1.6', color: 'var(--text-secondary)', marginTop: '1rem' }}>
          {t('about.abstract.p2')}
        </p>
        <p style={{ lineHeight: '1.6', color: 'var(--text-secondary)', marginTop: '1rem' }}>
          {t('about.abstract.p3')}
        </p>
      </div>

      {/* Key Findings & Methodology Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: '2rem',
        }}
      >
        {/* Methodology */}
        <div className="card">
          <div
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}
          >
            <span style={{ fontSize: '1.5rem' }}>🔬</span>
            <h3 style={{ margin: 0 }}>{t('about.methodology.title')}</h3>
          </div>
          <ul style={{ paddingLeft: '1.5rem', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>{t('about.methodology.framework').split(':')[0]}:</strong>
              {t('about.methodology.framework').split(':')[1]}
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>{t('about.methodology.dataset').split(':')[0]}:</strong>
              {t('about.methodology.dataset').split(':')[1]}
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>{t('about.methodology.models').split(':')[0]}:</strong>
              {t('about.methodology.models').split(':')[1]}
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>{t('about.methodology.baselines').split(':')[0]}:</strong>
              {t('about.methodology.baselines').split(':')[1]}
            </li>
          </ul>
        </div>

        {/* Key Findings */}
        <div className="card">
          <div
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}
          >
            <span style={{ fontSize: '1.5rem' }}>📊</span>
            <h3 style={{ margin: 0 }}>{t('about.findings.title')}</h3>
          </div>
          <ul style={{ paddingLeft: '1.5rem', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>{t('about.findings.performance').split(':')[0]}:</strong>
              {t('about.findings.performance').split(':')[1]}
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>{t('about.findings.size').split(':')[0]}:</strong>
              {t('about.findings.size').split(':')[1]}
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>{t('about.findings.hallucinations').split(':')[0]}:</strong>
              {t('about.findings.hallucinations').split(':')[1]}
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>{t('about.findings.gap').split(':')[0]}:</strong>
              {t('about.findings.gap').split(':')[1]}
            </li>
          </ul>
        </div>
      </div>

      {/* Contributors Section */}
      <div className="card">
        <h3>{t('about.team.title')}</h3>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '2rem',
            marginTop: '1rem',
          }}
        >
          <div>
            <h4 style={{ color: 'var(--accent-primary)', marginBottom: '0.5rem' }}>
              {t('about.team.authors')}
            </h4>
            <ul style={{ listStyle: 'none', padding: 0, margin: 0, color: 'var(--text-primary)' }}>
              <li style={{ padding: '0.25rem 0' }}>Muhoza Olivier Tuyishime</li>
              <li style={{ padding: '0.25rem 0' }}>William McAllister</li>
            </ul>
          </div>

          <div>
            <h4 style={{ color: 'var(--accent-secondary)', marginBottom: '0.5rem' }}>
              {t('about.team.supervisor')}
            </h4>
            <ul style={{ listStyle: 'none', padding: 0, margin: 0, color: 'var(--text-primary)' }}>
              <li style={{ padding: '0.25rem 0' }}>Alan Davoust</li>
            </ul>
          </div>

          <div>
            <h4 style={{ color: 'var(--text-tertiary)', marginBottom: '0.5rem' }}>
              {t('about.team.institution')}
            </h4>
            <p style={{ margin: 0, color: 'var(--text-secondary)' }}>
              {t('about.team.institutionName')}
              <br />
              {t('about.team.department')}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
