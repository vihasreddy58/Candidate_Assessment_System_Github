# SkillVerify - GitHub Candidate Assessment System

## 1. Project Description
SkillVerify is a GitHub-based candidate assessment platform. It ingests resumes (PDF/DOCX) or a bulk ZIP of resumes, extracts the candidate's GitHub profile, analyzes repositories and activity, compares resume skills to GitHub evidence, and generates a comprehensive report with scoring and recommendations. The frontend presents dashboards and can request a PDF rendered from the HTML report for professional output.

## 2. Setup

### Prerequisites
- Python 3.10+ (recommended)
- Node.js 18+ and npm
- GitHub token (optional but recommended for API rate limits)

### Backend (Flask)
```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

### Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```

### Combined (root scripts)
```bash
npm install
npm run dev-all
```

### Environment Variables
Create a .env file in the project root or backend folder:
```
GITHUB_TOKEN=your_token_here
FLASK_ENV=development
CLIENT_URL=http://localhost:5173
```

## 3. Module Explanation

### Backend
- app.py: Flask API entry point. Handles upload endpoints, orchestrates analysis pipeline, and exposes PDF generation.
- services/resume_parser.py: Extracts resume text and candidate fields, detects GitHub profile links.
- services/pdf_link_extractor.py: Robust GitHub URL extraction from PDF links and text.
- services/github_service.py: GitHub API client for profiles, repositories, languages, and commits.
- services/tech_stack_analyzer.py: Detects technologies from repo files and dependencies.
- services/skill_matcher.py: Matches resume skills to GitHub evidence and computes authenticity stats.
- services/code_quality_analyzer.py: Heuristic repo quality scoring (docs, structure, commit quality, optional code health).
- services/contribution_analyzer.py: Contribution patterns, recent activity, and repo-level contribution summaries.
- services/scoring_engine.py: Weighted overall scoring and rating.
- services/report_generator.py: Builds report JSON and renders PDF (Playwright primary, ReportLab fallback).

### Frontend
- src/App.jsx: App state and view switching for upload, dashboards, and reports.
- src/components/UploadSection.jsx: Single and bulk upload UI, file validation, API calls.
- src/components/BulkDashboard.jsx: Bulk results table, filtering, and export.
- src/components/Dashboard.jsx: Detailed report rendering and PDF export.
- src/components/LoadingScreen.jsx: Loading states during analysis.

### Documentation
- docs/project-overview.md: Full architecture and flow overview.
- docs/backend-methodology-research.md: Detailed backend methodology, scoring, and formulas.
- docs/scoring-deep-dive.md: Full scoring breakdown and rationale.

## 4. Pipeline

### Single Resume Flow
1. User uploads PDF/DOCX from frontend.
2. Backend extracts resume text and GitHub username.
3. GitHub profile and repositories are fetched.
4. Tech stack analysis detects technologies per repo.
5. Resume skills are matched against GitHub evidence.
6. Repo quality and code health are scored.
7. Contribution activity is summarized.
8. Final weighted score and recommendation are computed.
9. Report JSON is returned to frontend and rendered.
10. Optional PDF is generated from HTML via /api/analysis/download-report.

### Bulk ZIP Flow
1. User uploads ZIP containing multiple resumes.
2. Backend extracts files to a temp folder.
3. Each resume is processed through the same pipeline.
4. Summary table and per-candidate reports are returned.

## 5. Default Ports
- Backend: http://localhost:5000
- Frontend: http://localhost:5173

## 6. Notes
- GitHub API rate limits apply without a token.
- Resume extraction is heuristic and may miss context in complex formats.
- PDF generation relies on Playwright (Chromium download required on first run).
