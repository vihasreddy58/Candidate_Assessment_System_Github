import React, { useState, useRef } from 'react';
import axios from 'axios';
import { Upload, FileText, CheckCircle } from 'lucide-react';
import './UploadSection.css';

const UploadSection = ({ onAnalysisStart, onAnalysisComplete, onBulkAnalysisComplete, onError }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [githubUsername, setGithubUsername] = useState('');
  const [mode, setMode] = useState('single'); // 'single' or 'bulk'
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (file) => {
    if (mode === 'single') {
      const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
      if (!validTypes.includes(file.type)) {
        onError('Please upload a PDF or DOCX file');
        return;
      }
      if (file.size > 5 * 1024 * 1024) {
        onError('File size must be less than 5MB');
        return;
      }
    } else {
        // bulk mode expects a ZIP
      const isZip = file.name.toLowerCase().endsWith('.zip') || file.type === 'application/zip';
      if (!isZip) {
        onError('Please upload a ZIP file containing resumes (PDF/DOCX)');
        return;
      }
      if (file.size > 20 * 1024 * 1024) {
        onError('Zip size must be less than 20MB');
        return;
      }
    }

    setSelectedFile(file);
  };

  const handleFileInput = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (mode === 'single' && !selectedFile && !githubUsername.trim()) {
      onError('Please upload a resume or enter a GitHub username');
      return;
    }

    if (mode === 'bulk' && !selectedFile) {
      onError('Please select a ZIP file first');
      return;
    }

    onAnalysisStart();

    const formData = new FormData();
    if (mode === 'single') {
      if (selectedFile) {
        formData.append('resume', selectedFile);
      }
      if (githubUsername.trim()) {
        formData.append('github_username', githubUsername.trim());
      }
    } else {
      formData.append('resumes', selectedFile);
    }

    try {
      const url = mode === 'single' ? '/api/analysis/upload' : '/api/analysis/bulk-upload';
      const response = await axios.post(url, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      if (response.data.success) {
        if (mode === 'single') {
          onAnalysisComplete(response.data.report);
        } else {
          onBulkAnalysisComplete(response.data);
        }
      } else {
        onError(response.data.error || 'Analysis failed');
      }
    } catch (error) {
      const errorMessage = error.response?.data?.error || error.message || 'Failed to analyze resume(s)';
      onError(errorMessage);
    }
  };

  return (
    <div className="upload-section">
      <div className="upload-container">
        <div className="upload-header">
          <h2>Upload Resume for Analysis</h2>
          <p>Single resume or bulk ZIP of resumes (PDF/DOCX inside)</p>
          <div className="mode-toggle">
            <button className={mode === 'single' ? 'active' : ''} onClick={() => { setSelectedFile(null); setMode('single'); }}>Single</button>
            <button className={mode === 'bulk' ? 'active' : ''} onClick={() => { setSelectedFile(null); setGithubUsername(''); setMode('bulk'); }}>Bulk (ZIP)</button>
          </div>
        </div>

        {mode === 'single' && (
          <div className="github-input-row" style={{ marginBottom: '12px' }}>
            <label htmlFor="github-username" style={{ display: 'block', marginBottom: '6px', fontWeight: 600 }}>
              Or enter GitHub username directly
            </label>
            <input
              id="github-username"
              type="text"
              placeholder="e.g., octocat"
              value={githubUsername}
              onChange={(e) => setGithubUsername(e.target.value)}
              style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #d0d7e2' }}
            />
          </div>
        )}

        <div
          className={`drop-zone ${dragActive ? 'active' : ''} ${selectedFile ? 'has-file' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept={mode === 'single' ? '.pdf,.docx' : '.zip'}
            onChange={handleFileInput}
            style={{ display: 'none' }}
          />

          {!selectedFile ? (
            <>
              <Upload size={48} className="upload-icon" />
              <h3>Drop {mode === 'single' ? 'resume' : 'ZIP of resumes'} here or click to browse</h3>
              <p>{mode === 'single' ? 'PDF/DOCX up to 5MB' : 'ZIP up to 20MB containing PDF/DOCX files'}</p>
            </>
          ) : (
            <>
              <FileText size={48} className="file-icon" />
              <h3>{selectedFile.name}</h3>
              <p>{(selectedFile.size / 1024).toFixed(2)} KB</p>
              <button
                className="btn-change"
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedFile(null);
                }}
              >
                Change File
              </button>
            </>
          )}
        </div>

        {((mode === 'single' && (selectedFile || githubUsername.trim())) || (mode === 'bulk' && selectedFile)) && (
          <button className="btn-analyze" onClick={handleUpload}>
            Start Analysis
          </button>
        )}

        <div className="info-section">
          <h4>What This System Does</h4>
          <ul>
            <li><CheckCircle size={16} /> Extracts GitHub profile from resume</li>
            <li><CheckCircle size={16} /> Fetches all public repositories and activity</li>
            <li><CheckCircle size={16} /> Detects actual tech stack used in projects</li>
            <li><CheckCircle size={16} /> Compares resume skills with GitHub evidence</li>
            <li><CheckCircle size={16} /> Generates comprehensive hiring report</li>
          </ul>
        </div>

        <div className="requirements-section">
          <h4>Requirements</h4>
          <p>The resume must contain a GitHub profile link (e.g., github.com/username)</p>
        </div>
      </div>
    </div>
  );
};

export default UploadSection;
