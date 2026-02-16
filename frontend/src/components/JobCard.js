import React from 'react';

/**
 * JobCard component - Renders individual job listing with fit score and actions
 * Handles null fit_score checks internally
 */
const JobCard = ({ job, onViewPosting, onAnalyze, onGenerateDraft, loading }) => {
  return (
    <div className="job-card">
      <div className="job-card-header">
        <h3 className="job-title">{job.title}</h3>
        {job.fit_score != null && (
          <div className="fit-score-badge">
            <span className="fit-score-value">{job.fit_score.toFixed(1)}</span>
            <span className="fit-score-label">/100</span>
          </div>
        )}
      </div>
      
      <div className="job-meta">
        <div className="job-company">
          <span className="job-meta-icon">🏢</span>
          {job.company}
        </div>
        <div className="job-location">
          <span className="job-meta-icon">📍</span>
          {job.location || 'Remote'}
        </div>
      </div>

      {job.rationale && (
        <div className="job-rationale">
          <div className="rationale-label">Analysis:</div>
          <div className="rationale-text">{job.rationale}</div>
        </div>
      )}

      <div className="job-actions">
        <button 
          className="btn-secondary btn-sm" 
          onClick={() => onViewPosting(job.url)}
          disabled={!job.url || job.url === '#'}
          title="View job posting"
        >
          <span className="btn-icon">👁️</span>
          View
        </button>
        <button 
          className="btn-primary btn-sm" 
          onClick={() => onAnalyze(job.id)}
          disabled={loading}
          title="Analyze technical fit"
        >
          <span className="btn-icon">📊</span>
          Analyze
        </button>
        {job.fit_score >= 50 && (
          <button 
            className="btn-success btn-sm" 
            onClick={() => onGenerateDraft(job.id)}
            disabled={loading}
            title="Generate cover letter"
          >
            <span className="btn-icon">✍️</span>
            Draft
          </button>
        )}
      </div>
    </div>
  );
};

export default JobCard;
