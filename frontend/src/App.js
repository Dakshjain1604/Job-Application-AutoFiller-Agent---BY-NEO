import React, { useState, useEffect } from 'react';
import './App.css';
import SettingsModal from './components/SettingsModal';
import JobCard from './components/JobCard';
import Sidebar from './components/Sidebar';
import StatsOverview from './components/StatsOverview';
import ApplicationLog from './components/ApplicationLog';

function App() {
  const [activeTab, setActiveTab] = useState('config');
  const [config, setConfig] = useState({ keywords: '', salaryMin: '', salaryMax: '' });
  const [jobs, setJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [draft, setDraft] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState(null);
  const [backendStatus, setBackendStatus] = useState('checking');
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [apiKeyConfigured, setApiKeyConfigured] = useState(false);
  const [showLogs, setShowLogs] = useState(false);

  const API_BASE = 'http://localhost:8000';

  // Add log entry helper
  const addLog = (message) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs(prev => [...prev, { timestamp, message }]);
  };

  // Check backend connectivity and API key on mount
  useEffect(() => {
    const checkBackend = async () => {
      try {
        const response = await fetch(`${API_BASE}/`);
        if (response.ok) {
          setBackendStatus('connected');
          addLog('Backend connected successfully');
        } else {
          setBackendStatus('error');
          addLog('Backend connection error');
        }
      } catch (err) {
        setBackendStatus('error');
        setError('Cannot connect to backend. Make sure the server is running on port 8000.');
        addLog('Failed to connect to backend');
      }
    };
    checkBackend();

    // Check if API key is configured
    const apiKey = localStorage.getItem('openai_api_key');
    setApiKeyConfigured(!!apiKey);
  }, []);

  // Calculate average fit score
  const avgFitScore = jobs.length > 0 
    ? jobs.filter(j => j.fit_score != null).reduce((sum, j) => sum + j.fit_score, 0) / jobs.filter(j => j.fit_score != null).length
    : null;

  const uploadResume = async (file) => {
    setLoading(true);
    setError(null);
    addLog('Uploading resume...');
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await fetch(`${API_BASE}/upload-resume`, {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setProfile(data.profile);
      setError(null);
      addLog(`Resume uploaded successfully: ${data.profile.name}`);
    } catch (error) {
      console.error('Resume upload error:', error);
      setError('Error uploading resume: ' + error.message);
      addLog('Resume upload failed: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const searchJobs = async () => {
    if (!config.keywords.trim()) {
      setError('Please enter job keywords');
      return;
    }

    setLoading(true);
    setError(null);
    addLog(`Searching for jobs: ${config.keywords}`);
    
    try {
      const response = await fetch(`${API_BASE}/search-jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          keywords: config.keywords,
          salary_min: parseInt(config.salaryMin) || null,
          salary_max: parseInt(config.salaryMax) || null,
          max_jobs: 50
        })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setJobs(data.jobs || []);
      setActiveTab('jobs');
      setError(null);
      addLog(`Found ${data.jobs.length} jobs`);
    } catch (error) {
      console.error('Job search error:', error);
      setError('Error searching jobs: ' + error.message);
      addLog('Job search failed: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const analyzeJob = async (jobId) => {
    setLoading(true);
    setError(null);
    addLog(`Analyzing job ${jobId}...`);
    
    try {
      const apiKey = localStorage.getItem('openai_api_key');
      const response = await fetch(`${API_BASE}/analyze-job/${jobId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile_id: 1,
          api_key: apiKey || undefined
        })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Update job in the list with score
      setJobs(prevJobs => prevJobs.map(job => 
        job.id === jobId 
          ? { ...job, fit_score: data.analysis.score, rationale: data.analysis.rationale }
          : job
      ));
      
      setError(null);
      addLog(`Job ${jobId} analyzed: Score ${data.analysis.score.toFixed(1)}/100`);
    } catch (error) {
      console.error('Job analysis error:', error);
      setError('Error analyzing job: ' + error.message);
      addLog('Job analysis failed: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const generateDraft = async (jobId) => {
    setLoading(true);
    setError(null);
    addLog(`Generating cover letter for job ${jobId}...`);
    
    try {
      const apiKey = localStorage.getItem('openai_api_key');
      const response = await fetch(`${API_BASE}/generate-draft/${jobId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile_id: 1,
          api_key: apiKey || undefined
        })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      // FIX: Add job_id to draft object since backend doesn't return it
      setDraft({ ...data, job_id: jobId });
      setActiveTab('draft');
      setError(null);
      addLog('Cover letter generated successfully');
    } catch (error) {
      console.error('Draft generation error:', error);
      setError('Error generating draft: ' + error.message);
      addLog('Draft generation failed: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const viewJobPosting = (url) => {
    if (url && url !== '#') {
      addLog(`Opening job posting: ${url}`);
      window.open(url, '_blank');
    } else {
      setError('Job posting URL not available');
      addLog('Job posting URL not available');
    }
  };

  const renderConfig = () => (
    <div className="content-panel">
      <div className="panel-header">
        <h2 className="panel-title">Configuration</h2>
        <p className="panel-subtitle">Set up your job search parameters and upload your resume</p>
      </div>
      
      {error && (
        <div className="alert alert-error">
          <span className="alert-icon">⚠️</span>
          <span className="alert-message">{error}</span>
        </div>
      )}

      <div className="form-section">
        <label className="form-label">Upload Resume (PDF)</label>
        <div 
          className="file-upload-area"
          onClick={() => document.getElementById('resume-upload').click()}
        >
          <div className="file-upload-icon">📄</div>
          <div className="file-upload-content">
            <div className="file-upload-title">
              {profile ? `✓ ${profile.name}` : 'Click to upload resume'}
            </div>
            <div className="file-upload-subtitle">PDF format only</div>
          </div>
          <input
            id="resume-upload"
            type="file"
            accept=".pdf"
            style={{ display: 'none' }}
            onChange={(e) => {
              if (e.target.files[0]) {
                uploadResume(e.target.files[0]);
              }
            }}
          />
        </div>
      </div>

      <div className="form-section">
        <label className="form-label">Job Title Keywords</label>
        <input
          className="form-input"
          type="text"
          placeholder="e.g., Machine Learning Engineer, Data Scientist"
          value={config.keywords}
          onChange={(e) => setConfig({ ...config, keywords: e.target.value })}
        />
      </div>

      <div className="form-section">
        <label className="form-label">Target Salary Range (Optional)</label>
        <div className="form-row">
          <input
            className="form-input"
            type="number"
            placeholder="Min (e.g., 100000)"
            value={config.salaryMin}
            onChange={(e) => setConfig({ ...config, salaryMin: e.target.value })}
          />
          <input
            className="form-input"
            type="number"
            placeholder="Max (e.g., 200000)"
            value={config.salaryMax}
            onChange={(e) => setConfig({ ...config, salaryMax: e.target.value })}
          />
        </div>
      </div>

      <button 
        className="btn-primary" 
        onClick={searchJobs}
        disabled={loading || !config.keywords.trim()}
      >
        {loading ? (
          <>
            <span className="btn-spinner"></span>
            Searching...
          </>
        ) : (
          <>
            <span className="btn-icon">🔍</span>
            Search Jobs
          </>
        )}
      </button>
    </div>
  );

  const renderJobs = () => (
    <div className="content-panel">
      <div className="panel-header">
        <h2 className="panel-title">Job Opportunities</h2>
        <p className="panel-subtitle">{jobs.length} positions found</p>
      </div>
      
      {loading && (
        <div className="loading-overlay">
          <div className="spinner-large"></div>
          <div className="loading-text">Processing...</div>
        </div>
      )}

      {!loading && jobs.length === 0 && (
        <div className="empty-state">
          <div className="empty-state-icon">🔍</div>
          <div className="empty-state-title">No jobs found</div>
          <div className="empty-state-text">Try searching with different keywords</div>
        </div>
      )}

      <div className="jobs-grid">
        {jobs.map((job) => (
          <JobCard
            key={job.id}
            job={job}
            onViewPosting={viewJobPosting}
            onAnalyze={analyzeJob}
            onGenerateDraft={generateDraft}
            loading={loading}
          />
        ))}
      </div>
    </div>
  );

  const approveDraft = () => {
    if (!draft) return;
    addLog(`Cover letter approved for job ${draft.job_id}`);
    // Move to queue (for now, just log and clear draft)
    setDraft(null);
    setActiveTab('logs');
    setError(null);
  };

  const editDraft = () => {
    if (!draft) return;
    const newContent = prompt('Edit your cover letter:', draft.cover_letter);
    if (newContent !== null && newContent.trim() !== '') {
      setDraft({ ...draft, cover_letter: newContent });
      addLog('Cover letter edited');
      setError(null);
    }
  };

  const discardDraft = () => {
    if (!draft) return;
    if (window.confirm('Are you sure you want to discard this draft?')) {
      addLog('Cover letter draft discarded');
      setDraft(null);
      setActiveTab('jobs');
      setError(null);
    }
  };

  const renderDraft = () => (
    <div className="content-panel">
      <div className="panel-header">
        <h2 className="panel-title">Cover Letter Draft</h2>
        <p className="panel-subtitle">Review and edit before submission</p>
      </div>
      
      {!draft && (
        <div className="empty-state">
          <div className="empty-state-icon">✍️</div>
          <div className="empty-state-title">No draft generated yet</div>
          <div className="empty-state-text">Analyze a job and generate a draft from the Jobs tab</div>
        </div>
      )}

      {draft && (
        <div className="draft-container">
          <div className="draft-content">
            {draft.cover_letter}
          </div>
          <div className="draft-actions">
            <button className="btn-success" onClick={approveDraft}>
              <span className="btn-icon">✅</span>
              Approve & Queue
            </button>
            <button className="btn-secondary" onClick={editDraft}>
              <span className="btn-icon">✏️</span>
              Edit Draft
            </button>
            <button className="btn-danger" onClick={discardDraft}>
              <span className="btn-icon">🗑️</span>
              Discard
            </button>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-content">
          <h1 className="app-title">AutoCareer</h1>
          <p className="app-subtitle">AI-Powered Job Application Automation</p>
        </div>
      </header>

      <StatsOverview
        backendStatus={backendStatus}
        apiKeyConfigured={apiKeyConfigured}
        profile={profile}
        jobsCount={jobs.length}
        avgFitScore={avgFitScore}
        onSettingsClick={() => setSettingsOpen(true)}
      />

      <div className="app-layout">
        <Sidebar
          activeTab={activeTab}
          onTabChange={setActiveTab}
          jobsCount={jobs.length}
          logsCount={logs.length}
        />

        <main className="main-content">
          {activeTab === 'config' && renderConfig()}
          {activeTab === 'jobs' && renderJobs()}
          {activeTab === 'draft' && renderDraft()}
          {activeTab === 'logs' && (
            <ApplicationLog 
              logs={logs} 
              onClearLogs={() => setLogs([])} 
            />
          )}
        </main>
      </div>

      {/* Collapsible Activity History - Hidden by default */}
      {activeTab !== 'logs' && (
        <div className={`activity-history-container ${showLogs ? 'expanded' : 'collapsed'}`}>
          <button 
            className="activity-toggle"
            onClick={() => setShowLogs(!showLogs)}
            title={showLogs ? 'Hide Activity History' : 'Show Activity History'}
          >
            {showLogs ? '▼' : '▲'} Activity History {logs.length > 0 && `(${logs.length})`}
          </button>
          {showLogs && (
            <div className="activity-log-mini">
              {logs.slice(-10).reverse().map((log, idx) => (
                <div key={idx} className="log-entry-mini">
                  <span className="log-timestamp-mini">{log.timestamp}</span>
                  <span className="log-message-mini">{log.message}</span>
                </div>
              ))}
              {logs.length > 10 && (
                <div className="log-more" onClick={() => setActiveTab('logs')}>
                  View all {logs.length} logs →
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {settingsOpen && (
        <SettingsModal 
          isOpen={settingsOpen}
          onClose={() => setSettingsOpen(false)}
          onSave={(key) => {
            localStorage.setItem('openai_api_key', key);
            setApiKeyConfigured(!!key);
            addLog('API key updated');
          }}
        />
      )}
    </div>
  );
}

export default App;
