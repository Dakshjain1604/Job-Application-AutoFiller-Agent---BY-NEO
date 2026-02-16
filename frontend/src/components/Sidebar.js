import React from 'react';

/**
 * Sidebar component - Navigation and tab switching
 */
const Sidebar = ({ activeTab, onTabChange, jobsCount, logsCount }) => {
  const tabs = [
    { id: 'config', label: 'Configuration', icon: '⚙️' },
    { id: 'jobs', label: 'Jobs', icon: '💼', badge: jobsCount },
    { id: 'draft', label: 'Draft', icon: '✍️' },
    { id: 'logs', label: 'Logs', icon: '📋', badge: logsCount }
  ];

  return (
    <nav className="sidebar">
      <div className="sidebar-header">
        <h2 className="sidebar-title">Navigation</h2>
      </div>
      <ul className="sidebar-menu">
        {tabs.map(tab => (
          <li key={tab.id}>
            <button
              className={`sidebar-item ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => onTabChange(tab.id)}
            >
              <span className="sidebar-icon">{tab.icon}</span>
              <span className="sidebar-label">{tab.label}</span>
              {tab.badge !== undefined && tab.badge > 0 && (
                <span className="sidebar-badge">{tab.badge}</span>
              )}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
};

export default Sidebar;
