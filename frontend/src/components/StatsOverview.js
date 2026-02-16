import React from 'react';

/**
 * StatsOverview component - Displays system metrics and status indicators
 */
const StatsOverview = ({ 
  backendStatus, 
  apiKeyConfigured, 
  profile, 
  jobsCount, 
  avgFitScore,
  onSettingsClick 
}) => {
  const getStatusClass = (status) => {
    switch(status) {
      case 'connected': return 'status-success';
      case 'checking': return 'status-warning';
      case 'error': return 'status-error';
      default: return 'status-neutral';
    }
  };

  const stats = [
    {
      label: 'Backend',
      value: backendStatus.toUpperCase(),
      status: getStatusClass(backendStatus),
      icon: '🔌'
    },
    {
      label: 'API Key',
      value: apiKeyConfigured ? 'CONFIGURED' : 'NOT SET',
      status: apiKeyConfigured ? 'status-success' : 'status-error',
      icon: '🔑'
    },
    {
      label: 'Profile',
      value: profile ? profile.name : 'Not loaded',
      status: profile ? 'status-success' : 'status-neutral',
      icon: '👤'
    },
    {
      label: 'Jobs Found',
      value: jobsCount.toString(),
      status: 'status-neutral',
      icon: '💼'
    }
  ];

  if (avgFitScore !== null && avgFitScore !== undefined) {
    stats.push({
      label: 'Avg Fit Score',
      value: `${avgFitScore.toFixed(1)}/100`,
      status: avgFitScore >= 70 ? 'status-success' : avgFitScore >= 50 ? 'status-warning' : 'status-neutral',
      icon: '📊'
    });
  }

  return (
    <div className="stats-overview">
      <div className="stats-grid">
        {stats.map((stat, idx) => (
          <div key={idx} className="stat-card">
            <div className={`stat-indicator ${stat.status}`}></div>
            <div className="stat-content">
              <div className="stat-icon">{stat.icon}</div>
              <div className="stat-info">
                <div className="stat-label">{stat.label}</div>
                <div className="stat-value">{stat.value}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
      <button className="settings-btn" onClick={onSettingsClick} title="Open Settings">
        <span className="settings-icon">⚙️</span>
      </button>
    </div>
  );
};

export default StatsOverview;
