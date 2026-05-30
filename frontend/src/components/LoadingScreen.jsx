import React from 'react';
import { FileText, Link, BarChart3, Search, CheckCircle, FileOutput } from 'lucide-react';
import './LoadingScreen.css';

const LoadingScreen = () => {
  return (
    <div className="loading-screen">
      <div className="loading-content">
        <div className="spinner"></div>
        <h2>Analyzing Resume...</h2>
        <div className="loading-steps">
          <div className="step">
            <div className="step-icon"><FileText size={20} /></div>
            <p>Parsing resume content</p>
          </div>
          <div className="step">
            <div className="step-icon"><Link size={20} /></div>
            <p>Extracting GitHub profile</p>
          </div>
          <div className="step">
            <div className="step-icon"><BarChart3 size={20} /></div>
            <p>Fetching repository data</p>
          </div>
          <div className="step">
            <div className="step-icon"><Search size={20} /></div>
            <p>Analyzing tech stack</p>
          </div>
          <div className="step">
            <div className="step-icon"><CheckCircle size={20} /></div>
            <p>Matching skills</p>
          </div>
          <div className="step">
            <div className="step-icon"><FileOutput size={20} /></div>
            <p>Generating report</p>
          </div>
        </div>
        <p className="loading-note">This may take 30-60 seconds...</p>
      </div>
    </div>
  );
};

export default LoadingScreen;
