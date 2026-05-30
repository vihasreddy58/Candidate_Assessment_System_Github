import React, { useState } from 'react';
import {
  Download,
  Github,
  Award,
  TrendingUp,
  CheckCircle,
  XCircle,
  AlertCircle,
  BarChart3,
  Users,
  Star,
  GitFork,
  Code,
  FileText,
  TestTube,
  Settings,
  GitCommit,
  GitPullRequest,
  Activity,
  Calendar
} from 'lucide-react';
import { 
  PieChart, 
  Pie, 
  Cell, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend,
  ResponsiveContainer
} from 'recharts';
import './Dashboard.css';

const COLORS = ['#1e3a5f', '#2d5a87', '#4a7c9b', '#7ba3bc', '#10b981', '#f59e0b'];
const formatDateTime = (value) => (value ? new Date(value).toLocaleString() : 'N/A');
const QUALITY_LABELS = {
  documentation: 'Documentation',
  readiness: 'Project Readiness',
  testing: 'Testing',
  codeOrganization: 'Code Organization',
  maintainability: 'Maintainability',
  commitQuality: 'Commit Quality',
  codeHealth: 'Code Health'
};

const buildReportHtml = (report) => {
  const candidate = report.candidateSummary || {};
  const scoring = report.scoringAnalysis || {};
  const matching = report.skillMatchingReport || {};
  const matchingSummary = matching.summary || {};
  const skillMatchingSkipped = Boolean(matchingSummary.skipped);
  const codeQuality = report.codeQualityReport || {};
  const contributions = report.contributionReport || {};
  const contributionSummary = contributions.summary || {};
  const topRepos = contributions.topRepositories || [];
  const githubProfile = report.githubProfile || {};
  const githubStats = githubProfile.statistics || {};
  const githubActivity = githubProfile.activity || {};

  const listItems = (items, formatter) => (items && items.length ? items.map(formatter).join('') : '<li class="muted">No data available</li>');
  const limitList = (items, limit = 8) => (items || []).slice(0, limit);
  const categoryScores = codeQuality.categoryScores || {};

  return `<!DOCTYPE html>
  <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>${candidate.name || 'Candidate'} · Report</title>
      <style>
        * { box-sizing: border-box; }
        body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; background: #f4f5f7; color: #0f172a; margin: 0; padding: 16px; line-height: 1.5; }
        .sheet { background: #ffffff; max-width: 900px; margin: 0 auto; padding: 20px; border-radius: 14px; box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08); }
        .header { display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px; margin-bottom: 12px; }
        h1 { margin: 0 0 4px; font-size: 22px; }
        h2 { margin: 0 0 8px; font-size: 17px; }
        h3 { margin: 0 0 6px; font-size: 14px; }
        p { margin: 0 0 6px; color: #475569; }
        .eyebrow { text-transform: uppercase; letter-spacing: 0.08em; font-size: 11px; color: #64748b; margin: 0 0 4px; }
        .meta { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
        .pill { padding: 5px 8px; border-radius: 999px; font-weight: 600; background: #f8fafc; border: 1px solid #e2e8f0; color: #0f172a; font-size: 11px; }
        .pill.success { background: #ecfdf3; color: #0f5132; border-color: #bbf7d0; }
        .pill.warn { background: #fffbeb; color: #92400e; border-color: #fcd34d; }
        .pill.info { background: #eff6ff; color: #1d4ed8; border-color: #bfdbfe; }
        .section { margin: 14px 0 0; padding-top: 10px; border-top: 1px solid #e2e8f0; }
        .section-title { margin: 0 0 8px; font-size: 16px; }
        .grid { display: grid; gap: 8px; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }
        .card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px; }
        .muted { color: #475569; }
        .summary-table { width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 4px; }
        .summary-table th { text-align: left; background: #f1f5f9; padding: 6px 8px; border: 1px solid #e2e8f0; width: 24%; }
        .summary-table td { padding: 6px 8px; border: 1px solid #e2e8f0; }
        .table { width: 100%; border-collapse: collapse; margin-top: 6px; font-size: 12px; }
        .table th, .table td { padding: 6px 8px; border: 1px solid #e2e8f0; text-align: left; }
        .table th { background: #f1f5f9; }
        ul { padding-left: 16px; margin: 4px 0 0; }
        .list-tight li { margin: 2px 0; }
        .statline { display: flex; justify-content: space-between; font-weight: 600; margin-bottom: 4px; }
        .tagline { font-size: 12px; color: #475569; margin-top: 2px; }
      </style>
    </head>
    <body>
      <div class="sheet">
        <header class="header">
          <div>
            <p class="eyebrow">Candidate Report</p>
            <h1>${candidate.name || 'Candidate'}</h1>
            
          </div>
          <div class="meta">
            <span class="pill">GitHub: @${candidate.githubUsername || 'n/a'}</span>
            ${!skillMatchingSkipped ? `<span class="pill info">Match ${matchingSummary.matchPercentage || 0}%</span>` : ''}
            ${!skillMatchingSkipped ? `<span class="pill success">Overall ${scoring.overallScore || 0}/100 (${scoring.rating || 'N/A'})</span>` : ''}
            <span class="pill warn">Portfolio ${codeQuality.grade || 'N/A'}</span>
          </div>
        </header>

        <section class="section">
          <h2 class="section-title">Key Metrics</h2>
          <table class="summary-table">
            <tbody>
              ${!skillMatchingSkipped ? `<tr><th>Overall</th><td>${scoring.overallScore || 0}/100 · ${scoring.rating || 'N/A'}</td><th>Match</th><td>${matchingSummary.matchPercentage || 0}% (${matchingSummary.matchedSkills || 0} matched)</td></tr>` : ''}
              <tr><th>Repository Quality</th><td>${codeQuality.grade || 'N/A'} · ${codeQuality.gradeLabel || 'Not analyzed'}</td><th>Repos Analyzed</th><td>${codeQuality.repositoriesAnalyzed || 0}</td></tr>
              <tr><th>Commits</th><td>${contributionSummary.totalCommits || 0}</td><th>Active Repos</th><td>${contributionSummary.reposWithCommits || 0}</td></tr>
              <tr><th>Followers</th><td>${githubStats.followers || 0}</td><th>Public Repos</th><td>${githubStats.publicRepositories || 0}</td></tr>
            </tbody>
          </table>
          ${skillMatchingSkipped ? `<p class="muted" style="margin-top:8px;">Overall score is hidden because skill matching was skipped (${matchingSummary.skipReason || 'no resume skills'}).</p>` : ''}
        </section>

        ${!skillMatchingSkipped ? `<section class="section">
          <h2 class="section-title">Skill Matching</h2>
          <div class="grid">
            <div class="card">
              <div class="statline"><span>Summary</span><span>${matchingSummary.matchPercentage || 0}%</span></div>
              <p class="tagline">Matched ${matchingSummary.matchedSkills || 0} · Missing ${matchingSummary.missingSkills || 0} · Extra ${matchingSummary.extraSkills || 0}</p>
            </div>
            <div class="card">
              <h3>Matched Skills</h3>
              <ul class="list-tight">${listItems(limitList(matching.matchedSkills, 8), (s) => `<li>${s.resumeSkill} — ${s.matchType}</li>`)}</ul>
            </div>
            <div class="card">
              <h3>Missing Skills</h3>
              <ul class="list-tight">${listItems(limitList(matching.missingSkills, 8), (s) => `<li>${s.skill} — ${s.severity || 'medium'}</li>`)}</ul>
            </div>
            <div class="card">
              <h3>Additional Skills Found</h3>
              <ul class="list-tight">${listItems(limitList(matching.extraSkills, 8), (s) => `<li>${s.skill} (${s.category || 'other'})</li>`)}</ul>
            </div>
          </div>
        </section>` : ''}

        <section class="section">
          <h2 class="section-title">Repository Quality</h2>
          <div class="grid">
            <div class="card">
              <h3>Grade & Metrics</h3>
              <ul class="list-tight">
                <li>Grade: ${codeQuality.grade || 'N/A'} (${codeQuality.gradeLabel || 'Not analyzed'})</li>
                <li>Score: ${codeQuality.overallScore || 0}/100</li>
                <li>Readme coverage: ${(codeQuality.metrics?.readmePercentage || 0)}%</li>
                <li>Project readiness: ${(codeQuality.metrics?.readinessPercentage ?? codeQuality.metrics?.testingPercentage ?? 0)}%</li>
                <li>Maintainability: ${(codeQuality.categoryScores?.maintainability || 0)}%</li>
              </ul>
            </div>
            <div class="card">
              <h3>Category Scores</h3>
              <table class="table">
                <thead><tr><th>Category</th><th>Score</th></tr></thead>
                <tbody>
                  ${Object.entries(categoryScores).map(([key, val]) => `<tr><td>${QUALITY_LABELS[key] || key}</td><td>${val || 0}%</td></tr>`).join('') || '<tr><td colspan="2">No category scores</td></tr>'}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <section class="section">
          <h2 class="section-title">Contributions</h2>
          <div class="grid">
            <div class="card">
              <h3>Summary</h3>
              <ul class="list-tight">
                <li>Total commits: ${contributionSummary.totalCommits || 0}</li>
                <li>Active repos: ${contributionSummary.reposWithCommits || 0}</li>
                <li>Fork contributions: ${contributionSummary.forkContributions || 0}</li>
              </ul>
            </div>
            <div class="card">
              <h3>Top Repositories</h3>
              <ul class="list-tight">${listItems(limitList(topRepos, 6), (repo, idx) => `<li>#${idx + 1} ${repo.name} — ${repo.userCommits || 0} commits (${repo.language || 'N/A'})</li>`)}</ul>
            </div>
          </div>
        </section>

        <section class="section">
          <h2 class="section-title">GitHub Profile</h2>
          <div class="grid">
            <div class="card">
              <h3>Stats</h3>
              <ul class="list-tight">
                <li>Repositories: ${githubStats.publicRepositories || 0}</li>
                <li>Followers: ${githubStats.followers || 0}</li>
                <li>Stars: ${githubActivity.totalStars || 0}</li>
              </ul>
            </div>
            <div class="card">
              <h3>Activity</h3>
              <ul class="list-tight">
                <li>Active repositories: ${githubActivity.activeRepositories || 0}</li>
                <li>Recent activity: ${githubActivity.recentActivity?.isActive ? 'Active' : 'Inactive'}</li>
              </ul>
            </div>
          </div>
        </section>
      </div>
    </body>
  </html>`;
};
//report prop contains the complete analysis data from the backend
//onReset prop is a callback function to return to the upload screen for a new analysis.
//onBackToBulk allows returning to bulk summary when present.
const Dashboard = ({ report, onReset, onBackToBulk }) => {
  const [activeTab, setActiveTab] = useState('overview');
  const [downloading, setDownloading] = useState(false);
  const skillMatchingSkipped = Boolean(report?.skillMatchingReport?.summary?.skipped);

  const downloadReport = () => {
    const dataStr = JSON.stringify(report, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    const exportFileDefaultName = `hiring-report-${report.candidateSummary.githubUsername}-${Date.now()}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  };

  const downloadPdfFromHtml = () => {
    const html = buildReportHtml(report);
    setDownloading(true);
    fetch('http://localhost:5000/api/analysis/download-report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ html, name: report.candidateSummary.name })
    })
      .then(async (response) => {
        if (!response.ok) throw new Error('Failed to generate PDF');
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${report.candidateSummary.name || 'candidate'}_analysis.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      })
      .catch((error) => {
        console.error('Error generating PDF:', error);
        alert('Failed to generate PDF from report. Please try again.');
      })
      .finally(() => setDownloading(false));
  };

  const renderOverviewTab = () => (
    <div className="tab-content">
      {/* Candidate Summary */}
      <div className="section-card">
        <h2>Candidate Summary</h2>
        <div className="info-grid">
          <div className="info-item">
            <strong>Name:</strong> {report.candidateSummary.name}
          </div>
          <div className="info-item">
            <strong>Email:</strong> {report.candidateSummary.email || 'N/A'}
          </div>
          <div className="info-item">
            <strong>GitHub:</strong> 
            <a href={report.candidateSummary.githubUrl} target="_blank" rel="noopener noreferrer">
              @{report.candidateSummary.githubUsername}
            </a>
          </div>
          {report.candidateSummary.bio && (
            <div className="info-item full-width">
              <strong>Bio:</strong> {report.candidateSummary.bio}
            </div>
          )}
        </div>
      </div>

      {/* Score Cards */}
      <div className="score-cards">
        {!skillMatchingSkipped && (
          <div className="score-card">
            <div className="score-icon">
              <Award size={32} />
            </div>
            <div className="score-content">
              <h4>Overall Score</h4>
              <div className="score-value">{report.scoringAnalysis?.overallScore || 0}/100</div>
              <small>{report.scoringAnalysis?.rating || 'N/A'}</small>
            </div>
          </div>
        )}

        {!skillMatchingSkipped && (
          <>
            <div className="score-card">
              <div className="score-icon">
                <CheckCircle size={32} />
              </div>
              <div className="score-content">
                <h4>Skills Verified</h4>
                <div className="score-value">{report.skillMatchingReport?.summary?.matchedSkills || 0}/{report.skillMatchingReport?.summary?.totalResumeSkills || 0}</div>
                <small>from resume</small>
              </div>
            </div>

            <div className="score-card">
              <div className="score-icon">
                <Github size={32} />
              </div>
              <div className="score-content">
                <h4>Extra Skills Found</h4>
                <div className="score-value">{report.skillMatchingReport?.summary?.extraSkills || 0}</div>
                <small>on GitHub</small>
              </div>
            </div>

            <div className="score-card">
              <div className="score-icon">
                <BarChart3 size={32} />
              </div>
              <div className="score-content">
                <h4>Match Rate</h4>
                <div className="score-value">{report.skillMatchingReport?.summary?.matchPercentage || 0}%</div>
                <small>resume vs GitHub</small>
              </div>
            </div>
          </>
        )}

        <div className="score-card code-quality-card">
          <div className="score-icon">
            <Code size={32} />
          </div>
          <div className="score-content">
            <h4>Repository Quality</h4>
            <div className={`score-value grade-${(report.codeQualityReport?.grade || 'N').toLowerCase()}`}>{report.codeQualityReport?.grade || 'N/A'}</div>
            <small>{report.codeQualityReport?.gradeLabel || 'Not Analyzed'}</small>
          </div>
        </div>

        <div className="score-card">
          <div className="score-icon">
            <GitCommit size={32} />
          </div>
          <div className="score-content">
            <h4>Total Commits</h4>
            <div className="score-value">{report.contributionReport?.summary?.totalCommits || 0}</div>
            <small>across {report.contributionReport?.summary?.reposWithCommits || 0} repos</small>
          </div>
        </div>
      </div>

      {/* Scoring Breakdown */}
      <div className="section-card">
        <h3>Score Breakdown</h3>
        <div className="stat-grid">
          {!skillMatchingSkipped && (
            <div className="stat-item">
              <div className="stat-value">{report.scoringAnalysis?.scoreBreakdown?.skillAuthenticity ?? 0}</div>
              <div className="stat-label">Skill Authenticity</div>
            </div>
          )}
          <div className="stat-item">
            <div className="stat-value">{report.scoringAnalysis?.scoreBreakdown?.codeQuality ?? 0}</div>
            <div className="stat-label">Repository Quality</div>
          </div>
          <div className="stat-item">
            <div className="stat-value">{report.scoringAnalysis?.scoreBreakdown?.commitActivity ?? 0}</div>
            <div className="stat-label">Commit Activity</div>
          </div>
          <div className="stat-item">
            <div className="stat-value">{report.scoringAnalysis?.scoreBreakdown?.techStack ?? 0}</div>
            <div className="stat-label">Tech Stack</div>
          </div>
          <div className="stat-item">
            <div className="stat-value">{report.scoringAnalysis?.scoreBreakdown?.profileSignal ?? 0}</div>
            <div className="stat-label">Profile Signal</div>
          </div>
        </div>
      </div>
    </div>
  );

  const renderSkillsTab = () => {
    const matchData = [
      { name: 'Matched', value: report.skillMatchingReport.summary.matchedSkills, color: '#10b981' },
      { name: 'Missing', value: report.skillMatchingReport.summary.missingSkills, color: '#ef4444' },
      { name: 'Extra', value: report.skillMatchingReport.summary.extraSkills, color: '#1e3a5f' }
    ];

    return (
      <div className="tab-content">
        {/* Skill Match Summary */}
        <div className="section-card">
          <h2>Skill Matching Summary</h2>
          <div className="stat-grid">
            <div className="stat-item">
              <div className="stat-value">{report.skillMatchingReport.summary.matchPercentage}%</div>
              <div className="stat-label">Match Rate</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">{report.skillMatchingReport.summary.matchedSkills}</div>
              <div className="stat-label">Matched Skills</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">{report.skillMatchingReport.summary.missingSkills}</div>
              <div className="stat-label">Missing Skills</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">{report.skillMatchingReport.summary.extraSkills}</div>
              <div className="stat-label">Extra Skills Found</div>
            </div>
          </div>

          <div className="chart-container">
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={matchData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }) => `${name}: ${value}`}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {matchData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Matched Skills */}
        {report.skillMatchingReport.matchedSkills.length > 0 && (
          <div className="section-card">
            <h3><CheckCircle size={24} color="#52c41a" /> Verified Skills ({report.skillMatchingReport.matchedSkills.length})</h3>
            <div className="skills-list">
              {report.skillMatchingReport.matchedSkills.map((skill, idx) => (
                <div key={idx} className="skill-item matched">
                  <div className="skill-header">
                    <strong>{skill.resumeSkill}</strong>
                    {/* <span className="match-badge">{skill.matchType}</span> */}
                  </div>
                  
                  <div className="skill-repos">
                    <small>Found in: {skill.repositories.slice(0, 3).join(', ')}</small>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Missing Skills */}
        {report.skillMatchingReport.missingSkills.length > 0 && (
          <div className="section-card">
            <h3><XCircle size={24} color="#ff4d4f" /> Skills Not Found in GitHub ({report.skillMatchingReport.missingSkills.length})</h3>
            <div className="skills-list">
              {report.skillMatchingReport.missingSkills.map((skill, idx) => (
                <div key={idx} className="skill-item missing">
                  <div className="skill-header">
                    <strong>{skill.skill}</strong>
                    {/* <span className={`severity-badge ${skill.severity}`}>{skill.severity}</span> */}
                  </div>
                  <div className="skill-reason">
                    <small>{skill.reason}</small>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Extra Skills */}
        {report.skillMatchingReport.extraSkills.length > 0 && (
          <div className="section-card">
            <h3><AlertCircle size={24} color="#1890ff" /> Additional Skills Discovered ({report.skillMatchingReport.extraSkills.length})</h3>
            <div className="skills-list">
              {report.skillMatchingReport.extraSkills.map((skill, idx) => (
                <div key={idx} className="skill-item extra">
                  <div className="skill-header">
                    <strong>{skill.skill}</strong>
                    <span className="category-badge">{skill.category}</span>
                  </div>
                  <div className="skill-details">
                    {/* <span>Usage: {skill.usageFrequency}%</span> */}
                  </div>
                  <div className="skill-recommendation">
                    <small>{skill.recommendation}</small>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderCodeQualityTab = () => {
    const codeQuality = report.codeQualityReport || {};
    const metrics = codeQuality.metrics || {};
    const categoryScores = codeQuality.categoryScores || {};
    const strengths = codeQuality.strengths || [];
    const weaknesses = codeQuality.weaknesses || [];
    const suggestions = codeQuality.suggestions || [];

    const getGradeColor = (grade) => {
      const colors = {
        'A': '#10b981',
        'B': '#3b82f6',
        'C': '#f59e0b',
        'D': '#f97316',
        'F': '#ef4444'
      };
      return colors[grade] || '#6b7280';
    };

    const categoryData = [
      { name: 'Documentation', value: categoryScores.documentation || 0, color: '#3b82f6' },
      // { name: 'Project Readiness', value: categoryScores.readiness ?? categoryScores.testing ?? 0, color: '#10b981' },
      { name: 'Code Organization', value: categoryScores.codeOrganization || 0, color: '#8b5cf6' },
      // { name: 'Maintainability', value: categoryScores.maintainability || 0, color: '#f59e0b' },
      { name: 'Commits', value: categoryScores.commitQuality || 0, color: '#06b6d4' }
    ];

    if (categoryScores.codeHealth !== undefined && categoryScores.codeHealth !== null) {
      categoryData.push({ name: 'Code Quality', value: categoryScores.codeHealth || 0, color: '#7ba3bc' });
    }

    const codeHealthEnabled = Boolean(metrics.codeHealthEnabled);
    const codeHealthAvailable = Boolean(metrics.codeHealthAvailable);
    const codeHealthScore = metrics.codeHealthScore;
    const codeHealthLanguage = metrics.codeHealthLanguage;
    const codeHealthLanguages = Array.isArray(metrics.codeHealthLanguages) ? metrics.codeHealthLanguages : null;

    return (
      <div className="tab-content">
        {/* Grade Overview */}
        <div className="section-card grade-overview">
          <div className="grade-display">
            <div 
              className="grade-circle" 
              style={{ borderColor: getGradeColor(codeQuality.grade) }}
            >
              <span 
                className="grade-letter" 
                style={{ color: getGradeColor(codeQuality.grade) }}
              >
                {codeQuality.grade || 'N/A'}
              </span>
            </div>
            <div className="grade-info">
              <h2>Repository Quality</h2>
              <p className="grade-label">{codeQuality.gradeLabel || 'Not Analyzed'}</p>
              <p className="grade-score">Score: {codeQuality.overallScore || 0}/100</p>
              <p className="repos-analyzed">
                <Code size={16} /> {codeQuality.repositoriesAnalyzed || 0} repositories analyzed
              </p>
            </div>
          </div>
        </div>

        {/* Category Scores */}
        <div className="section-card">
          <h3><BarChart3 size={24} /> Portfolio Metrics by Category</h3>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={categoryData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" domain={[0, 100]} />
                <YAxis type="category" dataKey="name" width={120} />
                <Tooltip formatter={(value) => `${value}%`} />
                <Bar dataKey="value" name="Score" label={{ position: 'right', fill: '#333', fontSize: 12, formatter: (val) => `${val}%` }}>
                  {categoryData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {codeHealthEnabled && (
          <div className="section-card">
            <h3><Activity size={24} /> Code Quality (Static Analysis)</h3>
            <div className="info-grid">
              <div className="info-item">
                <strong>Score:</strong> {codeHealthAvailable ? `${codeHealthScore}/100` : 'N/A'}
              </div>
              <div className="info-item">
                <strong>Languages:</strong> {(codeHealthLanguages && codeHealthLanguages.length > 0)
                  ? codeHealthLanguages.join(', ')
                  : (codeHealthLanguage || 'N/A')}
              </div>
              <div className="info-item">
                <strong>Repos analyzed:</strong> {metrics.codeHealthReposAnalyzed ?? 0}
              </div>
              <div className="info-item">
                <strong>Files analyzed:</strong> {metrics.codeHealthFilesAnalyzed ?? 0}
              </div>
              <div className="info-item full-width">
                <strong>How it’s computed:</strong> Best-effort static analysis over sampled source files. Python prefers Radon (MI + CC). JS/TS and Java use AST-based complexity estimation.
              </div>
              <div className="info-item full-width">
                <strong>Formula (Python/Radon):</strong> `score = clamp(avgMI - penalty, 0, 100)` where `penalty = clamp(max(avgCC - 6, 0) * 4.5, 0, 28)`.
              </div>
            </div>
          </div>
        )}

        {/* Quick Stats */}
        {/* <div className="section-card">
          <h3>Quality Indicators Overview</h3>
          <div className="quality-stats-grid">
            <div className="quality-stat">
              <FileText size={28} />
              <div className="stat-value">{metrics.readmePercentage || 0}%</div>
              <div className="stat-label">Have README</div>
            </div>
            <div className="quality-stat">
              <TestTube size={28} />
              <div className="stat-value">{metrics.readinessPercentage ?? metrics.testingPercentage ?? 0}%</div>
              <div className="stat-label">Project Readiness</div>
            </div>
            <div className="quality-stat">
              <Settings size={28} />
              <div className="stat-value">{categoryScores.maintainability || 0}%</div>
              <div className="stat-label">Maintainability</div>
            </div>
            <div className="quality-stat">
              <GitCommit size={28} />
              <div className="stat-value">{categoryScores.commitQuality || 0}</div>
              <div className="stat-label">Commit Quality</div>
            </div>
          </div>
        </div> */}

        {/* Strengths & Weaknesses */}
        <div className="strengths-weaknesses-grid">
          {strengths.length > 0 && (
            <div className="section-card strengths-card">
              <h3><CheckCircle size={24} color="#10b981" /> Strengths</h3>
              <div className="sw-list">
                {strengths.map((item, idx) => (
                  <div key={idx} className="sw-item strength">
                    <strong>{item.area}</strong>
                    <p>{item.description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {weaknesses.length > 0 && (
            <div className="section-card weaknesses-card">
              <h3><XCircle size={24} color="#ef4444" /> Areas for Improvement</h3>
              <div className="sw-list">
                {weaknesses.map((item, idx) => (
                  <div key={idx} className="sw-item weakness">
                    <strong>{item.area}</strong>
                    <p>{item.description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Improvement Suggestions */}
        {suggestions.length > 0 && (
          <div className="section-card">
            <h3><AlertCircle size={24} color="#f59e0b" /> Improvement Suggestions</h3>
            <div className="suggestions-list">
              {suggestions.map((item, idx) => (
                <div key={idx} className={`suggestion-item priority-${item.priority}`}>
                  <div className="suggestion-header">
                    <span className="suggestion-category">{item.category}</span>
                    <span className={`priority-badge ${item.priority}`}>{item.priority}</span>
                  </div>
                  <p className="suggestion-text">{item.suggestion}</p>
                  <p className="suggestion-impact"><strong>Impact:</strong> {item.impact}</p>
                </div>
              ))}
            </div>
          </div>
        )}

      </div>
    );
  };

  const renderContributionsTab = () => {
    const contribution = report.contributionReport || {};
    const summary = contribution.summary || {};
    const topRepos = contribution.topRepositories || [];
    const contributions = contribution.contributionsToOthers || [];
    const activity = contribution.commitActivity || {};
    const streak = contribution.streak || {};

    const monthlyData = Object.entries(activity.monthlyActivity || {}).map(([month, count]) => ({
      name: month,
      commits: count
    }));

    const dailyData = Object.entries(activity.dailyDistribution || {}).map(([day, count]) => ({
      name: day.substring(0, 3),
      commits: count
    }));

    const topReposByCommits = topRepos.slice(0, 6).map((repo, idx) => ({
      name: repo.name,
      shortName: (repo.name || '').length > 16 ? `${repo.name.slice(0, 16)}...` : repo.name,
      commits: repo.userCommits || 0,
      stars: repo.stars || 0,
      fill: COLORS[idx % COLORS.length]
    }));

    return (
      <div className="tab-content">
        {/* Contribution Summary */}
        <div className="section-card">
          <h2><GitCommit size={28} /> Contribution Summary</h2>
          <div className="contribution-stats-grid">
            <div className="contribution-stat">
              <GitCommit size={32} />
              <div className="stat-value">{summary.totalCommits || 0}</div>
              <div className="stat-label">Total Commits</div>
            </div>
            <div className="contribution-stat">
              <Code size={32} />
              <div className="stat-value">{summary.reposWithCommits || 0}</div>
              <div className="stat-label">Active Repos</div>
            </div>
            <div className="contribution-stat">
              <GitPullRequest size={32} />
              <div className="stat-value">{summary.forkContributions || 0}</div>
              <div className="stat-label">Fork Contributions</div>
            </div>
            <div className="contribution-stat">
              <Calendar size={32} />
              <div className="stat-value">{streak.currentStreakMonths || 0}</div>
              <div className="stat-label">Month Streak</div>
            </div>
          </div>
          
          {summary.isActiveContributor && (
            <div className="active-contributor-badge">
              <Activity size={20} /> Active Contributor
            </div>
          )}
        </div>

        {/* Monthly Activity Chart */}
        {monthlyData.length > 0 && (
          <div className="section-card">
            <h3><BarChart3 size={24} /> Monthly Commit Activity</h3>
            <div className="chart-container">
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={monthlyData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="commits" fill="#1e3a5f" name="Commits" label={{ position: 'top', fill: '#333', fontSize: 11 }} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Daily Distribution */}
        {dailyData.length > 0 && (
          <div className="section-card">
            <h3><Calendar size={24} /> Commits by Day of Week</h3>
            <p className="section-subtitle">Most active day: <strong>{activity.mostActiveDay || 'Unknown'}</strong></p>
            <div className="chart-container">
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={dailyData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="commits" fill="#10b981" name="Commits" label={{ position: 'top', fill: '#333', fontSize: 11 }} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Top Repositories by Commits */}
        {topRepos.length > 0 && (
          <div className="section-card">
            <h3><Github size={24} /> Top Repositories by Commits</h3>
            <div className="top-repo-charts">
              <div className="chart-container">
                <p className="chart-note">Commit count by repository</p>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={topReposByCommits}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="shortName" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="commits" name="Commits" fill="#1e3a5f" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div className="top-repos-list">
              {topRepos.map((repo, idx) => (
                <div key={idx} className="top-repo-card">
                  <div className="top-repo-rank">#{idx + 1}</div>
                  <div className="top-repo-content">
                    <div className="top-repo-header">
                      <a href={repo.url} target="_blank" rel="noopener noreferrer">
                        <strong>{repo.name}</strong>
                      </a>
                      <div className="top-repo-badges">
                        <span className="language-badge">{repo.language}</span>
                        {repo.isActive && <span className="active-badge">Active</span>}
                      </div>
                    </div>
                    <div className="top-repo-stats">
                      <span><GitCommit size={14} /> {repo.userCommits} commits</span>
                      <span><Star size={14} /> {repo.stars}</span>
                    </div>
                    <div className="commit-quality-indicator">
                      Commit messages: <span className={`quality-${repo.commitMessageQuality}`}>{repo.commitMessageQuality}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Open Source Contributions */}
        {contributions.length > 0 && (
          <div className="section-card">
            <h3><GitPullRequest size={24} /> Contributions to Other Repositories</h3>
            {contribution.isOpenSourceContributor && (
              <div className="oss-badge">
                <CheckCircle size={18} /> Open Source Contributor
              </div>
            )}
            <div className="contributions-list">
              {contributions.map((contrib, idx) => (
                <div key={idx} className="contribution-card">
                  <div className="contribution-info">
                    <a href={contrib.url} target="_blank" rel="noopener noreferrer">
                      <strong>{contrib.name}</strong>
                    </a>
                    <span className="language-badge">{contrib.language}</span>
                  </div>
                  <div className="contribution-stats">
                    <span><GitCommit size={14} /> {contrib.commits} commits</span>
                    {contrib.lastContribution && (
                      <span className="last-contrib">Last: {new Date(contrib.lastContribution).toLocaleDateString()}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Streak Info */}
        <div className="section-card streak-card">
          <h3><TrendingUp size={24} /> Contribution Consistency</h3>
          <div className="streak-info">
            <div className="streak-item">
              <span className="streak-value">{streak.currentStreakMonths || 0}</span>
              <span className="streak-label">Current Streak (months)</span>
            </div>
            <div className="streak-item">
              <span className="streak-value">{streak.activeMonths || 0}</span>
              <span className="streak-label">Active Months</span>
            </div>
            <div className="streak-item">
              <span className={`consistency-badge ${streak.isConsistent ? 'consistent' : 'inconsistent'}`}>
                {streak.isConsistent ? 'Consistent' : 'Needs Improvement'}
              </span>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderGitHubTab = () => {
    const githubProfile = report.githubProfile || {};
    const languageDistribution = githubProfile.languageDistribution || {};
    const activity = githubProfile.activity || {};
    const statistics = githubProfile.statistics || {};
    const overview = githubProfile.overview || {};
    const repositoryInsights = report.repositoryInsights || {};
    const activityPattern = repositoryInsights.activityPattern || {};

    const languageData = Object.entries(languageDistribution).map(([name, data]) => ({
      name,
      value: parseFloat(data?.percentage || 0)
    }));

    return (
      <div className="tab-content">
        {/* GitHub Stats */}
        <div className="section-card">
          <h2><Github size={28} /> GitHub Profile Overview</h2>
          <div className="github-stats">
            <div className="stat-box">
              <Star size={32} />
              <div className="stat-value">{activity.totalStars || 0}</div>
              <div className="stat-label">Total Stars</div>
            </div>
            <div className="stat-box">
              <GitFork size={32} />
              <div className="stat-value">{activity.totalForks || 0}</div>
              <div className="stat-label">Total Forks</div>
            </div>
            <div className="stat-box">
              <Github size={32} />
              <div className="stat-value">{statistics.publicRepositories || 0}</div>
              <div className="stat-label">Repositories</div>
            </div>
            <div className="stat-box">
              <Users size={32} />
              <div className="stat-value">{statistics.followers || 0}</div>
              <div className="stat-label">Followers</div>
            </div>
          </div>

          <div className="account-info">
            <p><strong>Account Age:</strong> {overview.accountAge || 'N/A'}</p>
            <p><strong>Active Repositories:</strong> {activity.activeRepositories || 0}</p>
            <p><strong>Recent Activity:</strong> {activity.recentActivity?.isActive ? 'Active' : 'Inactive'}</p>
          </div>
        </div>

        {/* Language Distribution */}
        {languageData.length > 0 && (
          <div className="section-card">
            <h3>Language Distribution</h3>
            <div className="chart-container">
              <ResponsiveContainer width="100%" height={350}>
                <BarChart data={languageData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="value" fill="#1e3a5f" name="Percentage %" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Top Repositories */}
        {(repositoryInsights.topRepositories?.length || 0) > 0 && (
          <div className="section-card">
            <h3>Top Repositories</h3>
            <div className="repos-list">
              {repositoryInsights.topRepositories.slice(0, 5).map((repo, idx) => (
                <div key={idx} className="repo-card">
                  <div className="repo-header">
                    <a href={repo.url} target="_blank" rel="noopener noreferrer">
                      <strong>{repo.name}</strong>
                    </a>
                    <div className="repo-stats">
                      <span><Star size={14} /> {repo.stars || 0}</span>
                      <span><GitFork size={14} /> {repo.forks || 0}</span>
                    </div>
                  </div>
                  {repo.description && <p className="repo-description">{repo.description}</p>}
                  <div className="repo-meta">
                    <span className="repo-language">{repo.language || 'Unknown'}</span>
                    <span className="repo-updated">Updated: {repo.lastUpdated ? new Date(repo.lastUpdated).toLocaleDateString() : 'N/A'}</span>
                  </div>
                  {Object.keys(repo.detectedTechnologies || {}).length > 0 && (
                    <div className="repo-tech">
                      <strong>Tech Stack:</strong>
                      <div className="tech-tags">
                        {Object.keys(repo.detectedTechnologies).slice(0, 5).map((tech, i) => (
                          <span key={i} className="tech-tag">{tech}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Activity Pattern */}
        <div className="section-card">
          <h3>Activity Pattern</h3>
          <div className="activity-grid">
            <div className="activity-item">
              <div className="activity-count">{activityPattern.veryRecent || 0}</div>
              <div className="activity-label">Last 30 Days</div>
            </div>
            <div className="activity-item">
              <div className="activity-count">{activityPattern.recent || 0}</div>
              <div className="activity-label">Last 90 Days</div>
            </div>
            <div className="activity-item">
              <div className="activity-count">{activityPattern.moderate || 0}</div>
              <div className="activity-label">Last 180 Days</div>
            </div>
            <div className="activity-item">
              <div className="activity-count">{activityPattern.old || 0}</div>
              <div className="activity-label">Older</div>
            </div>
          </div>
          <div className="activity-level">
            <strong>Overall Activity Level:</strong> {activityPattern.activityLevel || 'Unknown'}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div className="dashboard-title">
          <p className="eyebrow">Candidate report</p>
          <h1>{report.candidateSummary.name}</h1>
          <div className="meta-bar">
            {!skillMatchingSkipped && (
              <span className="pill rating-pill">{report.scoringAnalysis?.rating || 'N/A'}</span>
            )}
            {!skillMatchingSkipped && (
              <span className="pill accent">Match {report.skillMatchingReport?.summary?.matchPercentage || 0}%</span>
            )}
            <span className="pill ghost">Portfolio {report.codeQualityReport?.grade || 'N/A'}</span>
            <span className="pill subtle">GitHub @{report.candidateSummary.githubUsername}</span>
          </div>
          <p className="report-meta">Generated: {formatDateTime(report.metadata.generatedAt)}</p>
          {skillMatchingSkipped && (
            <p className="report-meta">Skill matching skipped: {report.skillMatchingReport?.summary?.skipReason || 'No resume skills provided'}</p>
          )}
        </div>
        <div className="dashboard-actions">
          {onBackToBulk && (
            <button onClick={onBackToBulk} className="btn-secondary">
              Back to Results
            </button>
          )}
          <button onClick={downloadPdfFromHtml} className="btn-download btn-primary" disabled={downloading}>
            <Download size={20} />
            {downloading ? 'Preparing PDF...' : 'Download PDF'}
          </button>
          <button onClick={onReset} className="btn-new">
            New Analysis
          </button>
        </div>
      </div>

      <div className="dashboard-tabs">
        <button 
          className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          Overview
        </button>
        {!skillMatchingSkipped && (
          <button 
            className={`tab-btn ${activeTab === 'skills' ? 'active' : ''}`}
            onClick={() => setActiveTab('skills')}
          >
            Skills Analysis
          </button>
        )}
        <button 
          className={`tab-btn ${activeTab === 'codeQuality' ? 'active' : ''}`}
          onClick={() => setActiveTab('codeQuality')}
        >
          Repository Quality
        </button>
        <button 
          className={`tab-btn ${activeTab === 'contributions' ? 'active' : ''}`}
          onClick={() => setActiveTab('contributions')}
        >
          Contributions
        </button>
        <button 
          className={`tab-btn ${activeTab === 'github' ? 'active' : ''}`}
          onClick={() => setActiveTab('github')}
        >
          GitHub Profile
        </button>
      </div>

      <div className="dashboard-content">
        {activeTab === 'overview' && renderOverviewTab()}
        {!skillMatchingSkipped && activeTab === 'skills' && renderSkillsTab()}
        {activeTab === 'codeQuality' && renderCodeQualityTab()}
        {activeTab === 'contributions' && renderContributionsTab()}
        {activeTab === 'github' && renderGitHubTab()}
      </div>
    </div>
  );
};

export default Dashboard;
