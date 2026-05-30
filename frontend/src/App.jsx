import React, { useState } from 'react';
import UploadSection from './components/UploadSection';
import Dashboard from './components/Dashboard';
import LoadingScreen from './components/LoadingScreen';
import BulkDashboard from './components/BulkDashboard';
import './App.css';

function App() {
  const [report, setReport] = useState(null);
  const [bulkData, setBulkData] = useState(null);
  const [selectedReport, setSelectedReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleAnalysisComplete = (reportData) => {
    setReport(reportData);
    setBulkData(null);
    setSelectedReport(reportData);
    setLoading(false);
  };

  const handleBulkAnalysisComplete = (bulkResponse) => {
    setBulkData(bulkResponse);
    setSelectedReport(null);
    setReport(null);
    setLoading(false);
  };

  const handleAnalysisStart = () => {
    setLoading(true);
    setError(null);
  };

  const handleError = (errorMessage) => {
    setError(errorMessage);
    setLoading(false);
  };

  const handleReset = () => {
    setReport(null);
    setBulkData(null);
    setSelectedReport(null);
    setError(null);
    setLoading(false);
  };

  const handleSelectBulkReport = (id) => {
    if (!bulkData || !bulkData.reports) return;
    const reportItem = bulkData.reports.find((item) => item?.id === id) || bulkData.reports[id - 1];
    if (reportItem) {
      setSelectedReport(reportItem);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <div className="header-left">
            <div className="logo-section">
              <div className="logo-icon">
                <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
                  <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
                </svg>
              </div>
              <span className="logo-name">SkillVerify</span>
            </div>
          </div>
          <div className="header-center">
            <p className="header-tagline">GitHub Hiring Analysis Platform</p>
          </div>
        </div>
      </header>

      {loading && <LoadingScreen />}

      {error && (
        <div className="error-container">
          <div className="error-message">
            <div className="error-icon">
              <svg viewBox="0 0 24 24" width="48" height="48" fill="#dc3545">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
              </svg>
            </div>
            <h3>Analysis Error</h3>
            <p>{error}</p>
            <button onClick={handleReset} className="btn-primary">Try Again</button>
          </div>
        </div>
      )}

      {!loading && !error && !report && !bulkData && !selectedReport && (
        <UploadSection
          onAnalysisStart={handleAnalysisStart}
          onAnalysisComplete={handleAnalysisComplete}
           onBulkAnalysisComplete={handleBulkAnalysisComplete}
          onError={handleError}
        />
      )}

      {!loading && !error && bulkData && !selectedReport && (
        <BulkDashboard
          summary={bulkData.summary}
          failures={bulkData.failures}
          onSelectReport={handleSelectBulkReport}
          onReset={handleReset}
        />
      )}

      {!loading && !error && selectedReport && (
        <Dashboard
          report={selectedReport}
          onReset={bulkData ? () => setSelectedReport(null) : handleReset}
          onBackToBulk={bulkData ? () => setSelectedReport(null) : undefined}
        />
      )}

      <footer className="app-footer">
        <p>SkillVerify - Professional Hiring Analysis System | Powered by GitHub API</p>
      </footer>
    </div>
  );
}

export default App;
