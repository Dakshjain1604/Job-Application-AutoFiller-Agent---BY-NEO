import React from 'react';

/**
 * ApplicationLog component - Displays system activity logs with audit trail
 */
const ApplicationLog = ({ logs, onClearLogs }) => {
  return (
    <div className="application-log">
      <div className="log-header">
        <h2 className="log-title">System Activity Log</h2>
        {logs.length > 0 && (
          <button className="btn-danger btn-sm" onClick={onClearLogs}>
            <span className="btn-icon">🗑️</span>
            Clear
          </button>
        )}
      </div>

      <div className="log-container">
        {logs.length === 0 ? (
          <div className="log-empty">
            <div className="log-empty-icon">📋</div>
            <div className="log-empty-text">No activity logged yet</div>
            <div className="log-empty-subtext">System events will appear here</div>
          </div>
        ) : (
          <div className="log-entries">
            {logs.map((log, idx) => (
              <div key={idx} className="log-entry">
                <div className="log-timestamp">{log.timestamp}</div>
                <div className="log-message">{log.message}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {logs.length > 0 && (
        <div className="log-footer">
          <span className="log-count">{logs.length} {logs.length === 1 ? 'entry' : 'entries'}</span>
        </div>
      )}
    </div>
  );
};

export default ApplicationLog;
