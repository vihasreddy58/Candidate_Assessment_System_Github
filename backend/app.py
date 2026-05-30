import os
import json
import html
import tempfile
import traceback
import zipfile
import shutil
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from services.resume_parser import ResumeParser
from services.github_service import GitHubService
from services.tech_stack_analyzer import TechStackAnalyzer
from services.skill_matcher import SkillMatcher
from services.scoring_engine import ScoringEngine
from services.report_generator import ReportGenerator
from services.code_quality_analyzer import RepositoryQualityAnalyzer
from services.contribution_analyzer import ContributionAnalyzer

load_dotenv()


class MissingGithubUrl(Exception):
    """Raised when no GitHub URL is found in a resume."""

    def __init__(self, message, resume_data=None):
        super().__init__(message)
        self.resume_data = resume_data or {}


def _build_skipped_matching_results(reason='Skill matching skipped'):
    return {
        'matched_skills': [],
        'missing_skills': [],
        'extra_skills': [],
        'statistics': {
            'total_resume_skills': 0,
            'total_github_skills': 0,
            'matched_count': 0,
            'missing_count': 0,
            'extra_count': 0,
            'match_percentage': 0,
            'authenticity_score': 0,
            'skipped': True,
            'skip_reason': reason,
        },
    }


def _safe_html(value):
        if value is None:
                return 'N/A'
        return html.escape(str(value))


def _fmt_num(value, digits=1):
        if value is None:
                return 'N/A'
        try:
                return f"{float(value):.{digits}f}"
        except Exception:
                return _safe_html(value)


def _build_deep_scoring_html(report, scores, code_quality_data, contribution_data, matching_results, tech_stack_data, github_data):
    candidate = report.get('candidateSummary', {})
    scoring = report.get('scoringAnalysis', {})
    breakdown = scoring.get('scoreBreakdown', {})
    matching_summary = report.get('skillMatchingReport', {}).get('summary', {})
    matching_stats = matching_results.get('statistics', {}) or {}
    matching_skipped = bool(matching_summary.get('skipped') or matching_stats.get('skipped'))
    matching_skip_reason = matching_summary.get('skipReason') or matching_stats.get('skip_reason') or 'No resume skills provided'

    cq_metrics = code_quality_data.get('metrics', {})
    cq_model = code_quality_data.get('scoring_model', {})
    cq_repos = code_quality_data.get('detailed_analysis', [])

    contrib_summary = contribution_data.get('summary', {})
    commit_activity = contribution_data.get('commit_activity', {})
    contrib_stats = github_data.get('contribution_stats', {}) or {}

    detected_skills = tech_stack_data.get('detected_skills', {}) or {}
    github_profile = github_data.get('profile', {}) or {}
    github_repos = github_data.get('repositories', []) or []
    repo_meta_by_name = {r.get('name'): r for r in github_repos if r.get('name')}

    def _clamp(value, low=0.0, high=100.0):
        return max(low, min(high, value))

    def _parse_iso(value):
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        except Exception:
            return None

    def _days_since(dt_str):
        dt = _parse_iso(dt_str)
        if not dt:
            return None
        now = datetime.utcnow().replace(tzinfo=dt.tzinfo)
        return max((now - dt).days, 0)

    def _repo_recency_bonus(meta):
        days = _days_since(meta.get('pushed_at') or meta.get('updated_at')) if meta else None
        if days is None:
            return 0.0
        if days <= 30:
            return 1.0
        if days <= 90:
            return 0.6
        if days <= 180:
            return 0.3
        return 0.0

    def _score_account_maturity(created_at):
        dt = _parse_iso(created_at)
        if not dt:
            return 0.0
        now = datetime.utcnow().replace(tzinfo=dt.tzinfo)
        age_days = max((now - dt).days, 0)
        return _clamp((age_days / 1460.0) * 100.0, 0.0, 100.0)

    # Skill Authenticity derivation
    match_stats = matching_results.get('statistics', {}) or {}
    skill_auth_raw = float(match_stats.get('authenticity_score', 0) or 0)
    skill_match_pct = float(match_stats.get('match_percentage', 0) or 0)
    skill_auth_derived = max(skill_auth_raw, skill_match_pct)

    # Commit Activity derivation
    total_commits = float(contrib_summary.get('total_commits', 0) or 0)
    recent_commits = float(commit_activity.get('total_recent_commits', 0) or 0)
    recent_score = min(100.0, recent_commits * 4.0)
    volume_score = min(100.0, (total_commits / 200.0) * 100.0)
    commit_derived = (recent_score * 0.6) + (volume_score * 0.4)

    # Tech Stack derivation
    detected_count = len(detected_skills)
    breadth_score = min(detected_count, 25) / 25.0 * 100.0
    confidences = [float((v or {}).get('confidence', 0) or 0) for v in detected_skills.values()]
    avg_conf = (sum(confidences) / len(confidences)) if confidences else 0.0
    tech_stack_derived = (breadth_score * 0.6) + (avg_conf * 0.4)

    # Profile Signal derivation
    public_repos = float(github_profile.get('public_repos', 0) or 0)
    total_repos = float(contrib_stats.get('total_repositories', 0) or 0)
    active_repos = float(contrib_stats.get('active_repositories', 0) or 0)

    completeness_signals = [
        bool(github_profile.get('bio')),
        bool(github_profile.get('name')),
        bool(github_profile.get('location')),
        bool(github_profile.get('company')),
        bool(github_profile.get('blog')),
    ]
    completeness_score = (sum(1 for s in completeness_signals if s) / len(completeness_signals)) * 100.0
    depth_score = min(100.0, (public_repos / 25.0) * 100.0)
    active_volume_score = min(100.0, (active_repos / 8.0) * 100.0)
    base_repos = total_repos or public_repos
    activity_consistency_score = min(100.0, (active_repos / base_repos) * 100.0) if base_repos > 0 else 0.0
    account_maturity_score = _score_account_maturity(github_profile.get('created_at'))
    profile_derived = (
        (completeness_score * 0.20)
        + (depth_score * 0.25)
        + (active_volume_score * 0.30)
        + (activity_consistency_score * 0.15)
        + (account_maturity_score * 0.10)
    )

    # Repository Quality derivation + calibration details
    raw_scores = [float(r.get('score_raw', r.get('score', 0)) or 0) for r in cq_repos]
    if raw_scores:
        avg_raw = sum(raw_scores) / len(raw_scores)
        if len(raw_scores) > 1:
            variance = sum((s - avg_raw) ** 2 for s in raw_scores) / len(raw_scores)
            std_raw = variance ** 0.5
        else:
            std_raw = 10.0
        std_raw = max(std_raw, 8.0)
    else:
        avg_raw = 0.0
        std_raw = 8.0

    calibration_rows = []
    calibration_debug_by_repo = {}
    total_repo_weight = 0.0
    weighted_calibrated_sum = 0.0
    for repo in cq_repos:
        name = repo.get('name')
        meta = repo_meta_by_name.get(name, {})
        stars = float((meta or {}).get('stars', 0) or 0)
        recency_bonus = _repo_recency_bonus(meta or {})
        repo_weight = min(1.0 + (stars * 0.08) + recency_bonus, 5.0)

        raw = float(repo.get('score_raw', repo.get('score', 0)) or 0)
        z_scaled = 50.0 + (((raw - avg_raw) / std_raw) * 15.0)
        formula_calibrated = _clamp((raw * 0.75) + (z_scaled * 0.25) + 3.0, 0.0, 100.0)
        stored_calibrated = float(repo.get('score', 0) or 0)

        weighted_piece = stored_calibrated * repo_weight
        weighted_calibrated_sum += weighted_piece
        total_repo_weight += repo_weight

        calibration_debug_by_repo[name] = {
            'raw': raw,
            'z_scaled': z_scaled,
            'formula_calibrated': formula_calibrated,
            'stored_calibrated': stored_calibrated,
            'stars': stars,
            'recency_bonus': recency_bonus,
            'repo_weight': repo_weight,
            'weighted_piece': weighted_piece,
        }

        calibration_rows.append(
            '<tr>'
            f'<td>{_safe_html(name)}</td>'
            f'<td>{_fmt_num(raw, 2)}</td>'
            f'<td>{_fmt_num(z_scaled, 2)}</td>'
            f'<td>{_fmt_num(formula_calibrated, 2)}</td>'
            f'<td>{_fmt_num(stored_calibrated, 2)}</td>'
            f'<td>{_fmt_num(stars, 0)}</td>'
            f'<td>{_fmt_num(recency_bonus, 2)}</td>'
            f'<td>{_fmt_num(repo_weight, 2)}</td>'
            f'<td>{_fmt_num(weighted_piece, 2)}</td>'
            '</tr>'
        )

    cq_derived = (weighted_calibrated_sum / total_repo_weight) if total_repo_weight > 0 else 0.0
    calibration_html = ''.join(calibration_rows) if calibration_rows else '<tr><td colspan="9">No calibration rows available.</td></tr>'

    # Full per-repo trace across each scoring component.
    repo_component_trace_rows = []
    structure_base_map = {
        'excellent': 100.0,
        'good': 75.0,
        'basic': 50.0,
        'minimal': 25.0,
    }
    category_weights = {
        'documentation': 0.15,
        'code_organization': 0.30,
        'commit_quality': 0.25,
        'code_health': 0.30,
    }

    for repo in sorted(cq_repos, key=lambda r: float(r.get('score') or 0), reverse=True):
        name = repo.get('name')
        rs = repo.get('scores', {}) or {}
        ev = repo.get('evidence', {}) or {}
        calib = calibration_debug_by_repo.get(name, {})

        # Documentation component recompute.
        readme_quality_score = float(ev.get('readme_quality_score', 0) or 0)
        doc_calc = 0.0
        if ev.get('has_readme'):
            doc_calc += readme_quality_score * 0.65
        if ev.get('has_documentation'):
            doc_calc += 18.0
        if ev.get('has_architecture_doc'):
            doc_calc += 10.0
        if ev.get('has_examples'):
            doc_calc += 10.0
        if ev.get('readme_has_usage'):
            doc_calc += 7.0
        if ev.get('has_contributing'):
            doc_calc += 10.0
        doc_calc = _clamp(doc_calc, 0.0, 100.0)
        doc_stored = float(rs.get('documentation', 0) or 0)

        # Code organization component recompute.
        code_structure = str(ev.get('code_structure', 'basic') or 'basic').lower()
        structure_base = float(structure_base_map.get(code_structure, 25.0))
        directory_count = float(ev.get('directory_count', 0) or 0)
        richness_bonus = min(15.0, directory_count * 1.5)
        org_calc = _clamp((structure_base * 0.85) + richness_bonus, 0.0, 100.0)
        org_stored = float(rs.get('code_organization', 0) or 0)

        # Commit quality component recompute.
        freq_score = float(ev.get('commit_frequency_score', 0) or 0)
        msg_score = float(ev.get('commit_message_score', 0) or 0)
        commit_calc = _clamp((freq_score * 0.45) + (msg_score * 0.55), 0.0, 100.0)
        commit_stored = float(rs.get('commit_quality', 0) or 0)

        # Optional code-health component.
        ch_value = rs.get('code_health')
        ch_stored = float(ch_value or 0) if ch_value is not None else None

        # Raw weighted repository score recompute over active categories.
        active_components = []
        for key, wt in category_weights.items():
            val = rs.get(key)
            if val is None:
                continue
            active_components.append((float(val or 0), float(wt)))

        active_weight_sum = sum(w for _, w in active_components)
        raw_recomputed = 0.0
        if active_weight_sum > 0:
            raw_recomputed = _clamp(sum(v * w for v, w in active_components) / active_weight_sum, 0.0, 100.0)
        raw_stored = float(repo.get('score_raw', repo.get('score', 0)) or 0)

        repo_component_trace_rows.append(
            '<tr>'
            f'<td>{_safe_html(name)}</td>'
            f'<td>{_fmt_num(readme_quality_score, 1)}</td>'
            f'<td>{"Y" if ev.get("has_documentation") else "N"}/{"Y" if ev.get("has_architecture_doc") else "N"}/{"Y" if ev.get("has_examples") else "N"}/{"Y" if ev.get("readme_has_usage") else "N"}/{"Y" if ev.get("has_contributing") else "N"}</td>'
            f'<td>{_fmt_num(doc_calc, 2)} / {_fmt_num(doc_stored, 2)}</td>'
            f'<td>{_safe_html(code_structure)} ({_fmt_num(structure_base, 0)})</td>'
            f'<td>{_fmt_num(directory_count, 0)} -> {_fmt_num(richness_bonus, 2)}</td>'
            f'<td>{_fmt_num(org_calc, 2)} / {_fmt_num(org_stored, 2)}</td>'
            f'<td>{_fmt_num(freq_score, 2)}</td>'
            f'<td>{_fmt_num(msg_score, 2)}</td>'
            f'<td>{_fmt_num(commit_calc, 2)} / {_fmt_num(commit_stored, 2)}</td>'
            f'<td>{_fmt_num(ch_stored, 2) if ch_stored is not None else "N/A"}</td>'
            f'<td>{_fmt_num(raw_recomputed, 2)} / {_fmt_num(raw_stored, 2)}</td>'
            f'<td>{_fmt_num(calib.get("z_scaled"), 2)}</td>'
            f'<td>{_fmt_num(calib.get("formula_calibrated"), 2)} / {_fmt_num(calib.get("stored_calibrated"), 2)}</td>'
            f'<td>{_fmt_num(calib.get("repo_weight"), 2)}</td>'
            '</tr>'
        )

    repo_component_trace_html = ''.join(repo_component_trace_rows) if repo_component_trace_rows else '<tr><td colspan="15">No per-repo component trace available.</td></tr>'

    component_defs = [
        ('Skill Authenticity', 'skill_authenticity', breakdown.get('skillAuthenticity', 0), 0.60, skill_auth_derived),
        ('Repository Quality', 'code_quality', breakdown.get('codeQuality', 0), 0.10, cq_derived),
        ('Commit Activity', 'commit_activity', breakdown.get('commitActivity', 0), 0.10, commit_derived),
        ('Tech Stack', 'tech_stack', breakdown.get('techStack', 0), 0.10, tech_stack_derived),
        ('Profile Signal', 'profile_signal', breakdown.get('profileSignal', 0), 0.10, profile_derived),
    ]

    active_components = (scores.get('meta', {}) or {}).get('active_components') or [
        'skill_authenticity',
        'code_quality',
        'commit_activity',
        'tech_stack',
        'profile_signal',
    ]
    active_weights = {
        component_id: weight
        for _, component_id, _, weight, _ in component_defs
        if component_id in active_components
    }
    active_weight_sum = sum(active_weights.values()) or 1.0

    component_rows = []
    for name, component_id, score, base_weight, derived in component_defs:
        if matching_skipped and component_id == 'skill_authenticity':
            continue
        if component_id not in active_components:
            continue
        normalized_weight = base_weight / active_weight_sum
        component_rows.append((name, score, normalized_weight, derived))

    component_html = ''.join(
        (
            '<tr>'
            f'<td>{_safe_html(name)}</td>'
            f'<td>{_fmt_num(score, 2)}</td>'
            f'<td>{_fmt_num(weight * 100, 0)}%</td>'
            f'<td>{_fmt_num((float(score or 0) * weight), 2)}</td>'
            f'<td>{_fmt_num(derived, 2)}</td>'
            f'<td>{_fmt_num((float(derived or 0) - float(score or 0)), 2)}</td>'
            '</tr>'
        )
        for name, score, weight, derived in component_rows
    )

    repo_rows = []
    for repo in sorted(cq_repos, key=lambda r: float(r.get('score') or 0), reverse=True):
        rs = repo.get('scores', {}) or {}
        ev = repo.get('evidence', {}) or {}
        repo_rows.append(
            '<tr>'
            f'<td>{_safe_html(repo.get("name"))}</td>'
            f'<td>{_fmt_num(repo.get("score"), 1)}</td>'
            f'<td>{_fmt_num(repo.get("score_raw"), 1)}</td>'
            f'<td>{_safe_html(repo.get("grade", "N/A"))}</td>'
            f'<td>{_fmt_num(rs.get("documentation"), 1)}</td>'
            f'<td>{_fmt_num(rs.get("code_organization"), 1)}</td>'
            f'<td>{_fmt_num(rs.get("commit_quality"), 1)}</td>'
            f'<td>{_fmt_num(rs.get("code_health"), 1)}</td>'
            f'<td>{"Yes" if ev.get("has_readme") else "No"}</td>'
            f'<td>{_safe_html(ev.get("commit_frequency", "N/A"))}</td>'
            f'<td>{_safe_html(ev.get("commit_message_quality", "N/A"))}</td>'
            '</tr>'
        )
    repo_html = ''.join(repo_rows) if repo_rows else '<tr><td colspan="11">No repository-level quality details found.</td></tr>'

    generated_at = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    overall_pill_html = '' if matching_skipped else f'<span class="pill">Overall: {_fmt_num(scoring.get("overallScore"), 2)}/100</span>'
    rating_pill_html = '' if matching_skipped else f'<span class="pill">Rating: {_safe_html(scoring.get("rating", "N/A"))}</span>'
    skill_match_pill_html = '' if matching_skipped else f'<span class="pill">Skill Match: {_fmt_num(matching_summary.get("matchPercentage"), 1)}%</span>'
    overall_total_row_html = '' if matching_skipped else f'<tr><th colspan="3">Total</th><th>{_fmt_num(scores.get("overall"), 2)}</th><th colspan="2">n/a</th></tr>'
    overall_hidden_note_html = '' if not matching_skipped else f'<div class="meta">Overall score hidden: skill matching skipped ({_safe_html(matching_skip_reason)})</div>'

    return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
    <title>{_safe_html(candidate.get('githubUsername') or candidate.get('name') or 'candidate')} - Deep Scoring Analysis</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f3f7fc; color: #0f172a; margin: 0; padding: 24px; }}
        .container {{ max-width: 1220px; margin: 0 auto; }}
        .card {{ background: #fff; border: 1px solid #dbe4f0; border-radius: 10px; padding: 16px; margin-bottom: 16px; }}
        h1, h2 {{ margin: 0 0 10px; }}
        .meta {{ color: #475569; font-size: 13px; margin-top: 4px; }}
        .pills {{ margin-top: 10px; }}
        .pill {{ display: inline-block; padding: 5px 9px; border-radius: 999px; border: 1px solid #bfd1f2; background: #eef4ff; font-size: 12px; margin-right: 8px; margin-bottom: 8px; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 8px; }}
        th, td {{ border: 1px solid #dbe4f0; padding: 8px; text-align: left; vertical-align: top; }}
        th {{ background: #eef3ff; }}
        .grid {{ display: grid; gap: 10px; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }}
        .formula {{ background: #f8fafc; border: 1px solid #dbe4f0; border-radius: 8px; padding: 10px; font-family: Consolas, monospace; font-size: 12px; white-space: pre-wrap; margin-top: 10px; }}
        .small {{ font-size: 12px; color: #334155; }}
    </style>
</head>
<body>
    <div class=\"container\">
        <div class=\"card\">
            <h1>Deep Scoring Analysis</h1>
            <div class=\"meta\">Generated: {_safe_html(generated_at)}</div>
            <div class=\"meta\">Candidate: {_safe_html(candidate.get('name') or 'Unknown')} | GitHub: @{_safe_html(candidate.get('githubUsername') or 'N/A')}</div>
            {overall_hidden_note_html}
            <div class=\"pills\">
                {overall_pill_html}
                {rating_pill_html}
                <span class=\"pill\">Repo Quality: {_fmt_num(code_quality_data.get('overall_score'), 1)} ({_safe_html(code_quality_data.get('grade', 'N/A'))})</span>
                {skill_match_pill_html}
            </div>
        </div>

        <div class=\"card\">
            <h2>Final Scoring Components</h2>
            <table>
                <thead><tr><th>Component</th><th>Score (stored)</th><th>Weight</th><th>Weighted Contribution</th><th>Score (derived)</th><th>Derived - Stored</th></tr></thead>
                <tbody>
                    {component_html}
                    {overall_total_row_html}
                </tbody>
            </table>
            <div class="formula">Skill Authenticity = max(authenticity_score, match_percentage)
Commit Activity = (min(100, recent_commits * 4) * 0.60) + (min(100, total_commits/200*100) * 0.40)
Tech Stack = (breadth_score * 0.60) + (avg_confidence * 0.40)
Profile Signal = completeness*0.20 + depth*0.25 + active_volume*0.30 + consistency*0.15 + account_maturity*0.10
Repository Quality = weighted mean of calibrated repo scores (weight = min(1 + stars*0.08 + recency_bonus, 5))</div>
        </div>

        <div class="card">
            <h2>Per-Repo Full Component Trace</h2>
            <div class="formula">Doc formula:
doc = clamp((has_readme ? readme_quality_score * 0.65 : 0) + (has_docs ? 18 : 0) + (has_arch ? 10 : 0) + (has_examples ? 10 : 0) + (readme_usage ? 7 : 0) + (has_contributing ? 10 : 0), 0, 100)

Org formula:
org = clamp((structure_base * 0.85) + min(15, directory_count * 1.5), 0, 100)

Commit formula:
commit = clamp((commit_frequency_score * 0.45) + (commit_message_score * 0.55), 0, 100)

Raw repo score formula (active categories renormalized):
raw = sum(component_score_i * weight_i) / sum(active_weight_i)
where weights = doc:0.15, org:0.30, commit:0.25, code_health:0.30 (if available)

Calibration formula:
z_scaled = 50 + ((raw - avg_raw) / max(std_raw, 8)) * 15
calibrated = clamp((raw * 0.75) + (z_scaled * 0.25) + 3, 0, 100)</div>
            <p class="small">Docs flags order: has_docs/has_architecture_doc/has_examples/readme_has_usage/has_contributing</p>
            <table>
                <thead>
                    <tr>
                        <th>Repo</th>
                        <th>README Score</th>
                        <th>Docs Flags</th>
                        <th>Doc Calc / Stored</th>
                        <th>Structure</th>
                        <th>Dir -> Bonus</th>
                        <th>Org Calc / Stored</th>
                        <th>Freq Score</th>
                        <th>Msg Score</th>
                        <th>Commit Calc / Stored</th>
                        <th>Code Health</th>
                        <th>Raw Recalc / Stored</th>
                        <th>Z-scaled</th>
                        <th>Calib Calc / Stored</th>
                        <th>Repo Weight</th>
                    </tr>
                </thead>
                <tbody>{repo_component_trace_html}</tbody>
            </table>
        </div>

        <div class="card">
            <h2>Component Derivation Inputs</h2>
            <div class="grid">
                <div><strong>Skill authenticity (raw):</strong> {_fmt_num(skill_auth_raw, 2)}</div>
                <div><strong>Match percentage:</strong> {_fmt_num(skill_match_pct, 2)}</div>
                <div><strong>Skill authenticity (derived):</strong> {_fmt_num(skill_auth_derived, 2)}</div>
                <div><strong>Total commits:</strong> {_fmt_num(total_commits, 0)}</div>
                <div><strong>Recent commits:</strong> {_fmt_num(recent_commits, 0)}</div>
                <div><strong>Commit recent score:</strong> {_fmt_num(recent_score, 2)}</div>
                <div><strong>Commit volume score:</strong> {_fmt_num(volume_score, 2)}</div>
                <div><strong>Commit activity (derived):</strong> {_fmt_num(commit_derived, 2)}</div>
                <div><strong>Detected skills count:</strong> {_fmt_num(detected_count, 0)}</div>
                <div><strong>Tech breadth score:</strong> {_fmt_num(breadth_score, 2)}</div>
                <div><strong>Avg skill confidence:</strong> {_fmt_num(avg_conf, 2)}</div>
                <div><strong>Tech stack (derived):</strong> {_fmt_num(tech_stack_derived, 2)}</div>
                <div><strong>Profile completeness:</strong> {_fmt_num(completeness_score, 2)}</div>
                <div><strong>Depth score:</strong> {_fmt_num(depth_score, 2)}</div>
                <div><strong>Active volume score:</strong> {_fmt_num(active_volume_score, 2)}</div>
                <div><strong>Activity consistency:</strong> {_fmt_num(activity_consistency_score, 2)}</div>
                <div><strong>Account maturity score:</strong> {_fmt_num(account_maturity_score, 2)}</div>
                <div><strong>Profile signal (derived):</strong> {_fmt_num(profile_derived, 2)}</div>
            </div>
        </div>

        <div class=\"card\">
            <h2>Code Health and Repository Quality Signals</h2>
            <div class=\"grid\">
                <div><strong>Code health enabled:</strong> {'Yes' if cq_model.get('code_health_enabled') else 'No'}</div>
                <div><strong>Code health score:</strong> {_fmt_num(cq_metrics.get('avg_code_health_score'), 1)}</div>
                <div><strong>Code health repos analyzed:</strong> {_safe_html(cq_metrics.get('code_health_repos_analyzed', 0))}</div>
                <div><strong>Code health files analyzed:</strong> {_safe_html(cq_metrics.get('code_health_files_analyzed', 0))}</div>
                <div><strong>Code health languages:</strong> {_safe_html(', '.join(cq_metrics.get('code_health_languages', []) or []))}</div>
                <div><strong>README coverage:</strong> {_fmt_num(cq_metrics.get('readme_percentage'), 1)}%</div>
                <div><strong>Avg documentation:</strong> {_fmt_num(cq_metrics.get('avg_documentation_score'), 1)}</div>
                <div><strong>Avg code organization:</strong> {_fmt_num(cq_metrics.get('avg_code_organization_score'), 1)}</div>
                <div><strong>Avg commit quality:</strong> {_fmt_num(cq_metrics.get('avg_commit_quality_score'), 1)}</div>
                <div><strong>Calibration avg(raw):</strong> {_fmt_num(avg_raw, 2)}</div>
                <div><strong>Calibration std(raw):</strong> {_fmt_num(std_raw, 2)}</div>
                <div><strong>Total repo weight:</strong> {_fmt_num(total_repo_weight, 2)}</div>
                <div><strong>Repo quality (derived weighted):</strong> {_fmt_num(cq_derived, 2)}</div>
            </div>
            <div class="formula">Per-repo calibration:
z_scaled = 50 + ((raw - avg_raw) / max(std_raw, 8)) * 15
calibrated = clamp((raw * 0.75) + (z_scaled * 0.25) + 3, 0, 100)
portfolio_repo_quality = sum(calibrated_i * weight_i) / sum(weight_i)</div>
        </div>

        <div class="card">
            <h2>Calibration Table (Raw -> Calibrated)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Repository</th>
                        <th>Raw</th>
                        <th>Z-scaled</th>
                        <th>Calibrated (formula)</th>
                        <th>Calibrated (stored)</th>
                        <th>Stars</th>
                        <th>Recency Bonus</th>
                        <th>Repo Weight</th>
                        <th>Weighted Piece</th>
                    </tr>
                </thead>
                <tbody>{calibration_html}</tbody>
            </table>
        </div>

        <div class=\"card\">
            <h2>Per-Repository Deep Breakdown</h2>
            <table>
                <thead>
                    <tr>
                        <th>Repository</th>
                        <th>Calibrated</th>
                        <th>Raw</th>
                        <th>Grade</th>
                        <th>Docs</th>
                        <th>Org</th>
                        <th>Commit</th>
                        <th>Code Health</th>
                        <th>README</th>
                        <th>Commit Frequency</th>
                        <th>Commit Message</th>
                    </tr>
                </thead>
                <tbody>{repo_html}</tbody>
            </table>
        </div>

        <div class=\"card\">
            <h2>Additional Scoring Inputs</h2>
            <div class=\"grid\">
                <div><strong>Matched skills:</strong> {_safe_html(matching_summary.get('matchedSkills', 0))}</div>
                <div><strong>Missing skills:</strong> {_safe_html(matching_summary.get('missingSkills', 0))}</div>
                <div><strong>Extra skills:</strong> {_safe_html(matching_summary.get('extraSkills', 0))}</div>
                <div><strong>Detected stack skills:</strong> {_safe_html(len(detected_skills))}</div>
                <div><strong>Total commits:</strong> {_safe_html(contrib_summary.get('total_commits', 0))}</div>
                <div><strong>Recent commits:</strong> {_safe_html(commit_activity.get('total_recent_commits', 0))}</div>
                <div><strong>Repos with commits:</strong> {_safe_html(contrib_summary.get('repos_with_commits', 0))}</div>
                <div><strong>Public repos:</strong> {_safe_html(github_profile.get('public_repos', 0))}</div>
                <div><strong>Followers:</strong> {_safe_html(github_profile.get('followers', 0))}</div>
            </div>
        </div>
    </div>
</body>
</html>
"""


def _save_deep_scoring_report(report, scores, code_quality_data, contribution_data, matching_results, tech_stack_data, github_data):
        project_root = os.path.dirname(os.path.dirname(__file__))
        candidate = report.get('candidateSummary', {})
        slug = candidate.get('githubUsername') or candidate.get('name') or 'candidate'
        safe_slug = ''.join(ch if ch.isalnum() or ch in ('-', '_') else '_' for ch in str(slug)).strip('_') or 'candidate'

        filename = f"{safe_slug}_deep_scoring_analysis.html"
        path = os.path.join(project_root, filename)

        html_content = _build_deep_scoring_html(
                report,
                scores,
                code_quality_data,
                contribution_data,
                matching_results,
                tech_stack_data,
                github_data,
        )

        with open(path, 'w', encoding='utf-8') as f:
                f.write(html_content)

        return path


def process_resume_file(filepath, github_username_fallback=None):
    """Run full analysis pipeline for a single resume file and return (report, resume_data)."""

    def _truncate(value, *, max_items: int = 8, max_str: int = 500, _depth: int = 0, _max_depth: int = 5):
        if _depth > _max_depth:
            return "<truncated-depth>"

        if isinstance(value, str):
            return value if len(value) <= max_str else (value[:max_str] + "…")
        if isinstance(value, (int, float, bool)) or value is None:
            return value
        if isinstance(value, dict):
            return {
                str(k): _truncate(v, max_items=max_items, max_str=max_str, _depth=_depth + 1, _max_depth=_max_depth)
                for k, v in list(value.items())[:max_items]
            }
        if isinstance(value, (list, tuple)):
            clipped = list(value)[:max_items]
            out = [_truncate(v, max_items=max_items, max_str=max_str, _depth=_depth + 1, _max_depth=_max_depth) for v in clipped]
            if len(value) > max_items:
                out.append(f"… (+{len(value) - max_items} more)")
            return out
        return str(value)

    def _print_stage(title: str, payload=None):
        print("\n" + "=" * 80, flush=True)
        print(f"[PIPELINE] {title}", flush=True)
        if payload is not None:
            try:
                print(json.dumps(_truncate(payload), indent=2, ensure_ascii=False, default=str), flush=True)
            except Exception:
                print(str(payload), flush=True)

    # Always print intermediate results. Limit per-repo output to keep the console readable.
    per_repo_limit = int(os.getenv("PIPELINE_DEBUG_REPOS", "10") or 10)

    if str(filepath).lower().endswith('.json'):
        with open(filepath, 'r', encoding='utf-8') as f:
            resume_data = json.load(f)
    else:
        resume_parser = ResumeParser()
        resume_data = resume_parser.parse(filepath)

    _print_stage(
        "Resume parsed",
        {
            "name": resume_data.get("name"),
            "email": resume_data.get("email"),
            "phone": resume_data.get("phone"),
            "github_url": resume_data.get("github_url"),
            "skills_count": len(resume_data.get("skills", []) or []),
            "skills_sample": (resume_data.get("skills", []) or [])[:15],
        },
    )

    if not resume_data.get('github_url') and github_username_fallback:
        resume_data['github_url'] = github_username_fallback.strip()

    if not resume_data.get('github_url'):
        raise MissingGithubUrl(
            'No GitHub profile URL found in resume. Please ensure your resume contains a GitHub link.',
            resume_data
        )

    github_service = GitHubService()
    github_data = github_service.fetch_user_data(resume_data['github_url'])

    _print_stage(
        "GitHub data fetched",
        {
            "username": github_data.get("profile", {}).get("login"),
            "public_repos": github_data.get("profile", {}).get("public_repos"),
            "repos_fetched": len(github_data.get("repositories", []) or []),
            "language_stats": github_data.get("language_stats", {}),
            "contribution_stats": github_data.get("contribution_stats", {}),
            "top_repos": [
                {"name": r.get("name"), "updated_at": r.get("updated_at")}
                for r in (github_data.get("repositories", []) or [])[:min(per_repo_limit, 10)]
            ],
        },
    )

    tech_stack_analyzer = TechStackAnalyzer(github_service)
    tech_stack_data = tech_stack_analyzer.analyze_repositories(github_data['repositories'])

    _print_stage(
        "Tech stack analyzed",
        {
            "total_repos_analyzed": tech_stack_data.get("total_repos_analyzed"),
            "detected_skills_count": len((tech_stack_data.get("detected_skills") or {})),
            "skills_considered_for_scoring": sorted(list((tech_stack_data.get("detected_skills") or {}).keys())),
            "per_repo_detected_technologies": [
                {
                    "repo": rd.get("name"),
                    "language": rd.get("language"),
                    "stars": rd.get("stars"),
                    "detected": sorted(
                        [
                            {
                                "tech": t,
                                # "confidence": (d or {}).get("confidence"),
                                "type": (d or {}).get("type"),
                                "evidence": (d or {}).get("evidence", [])[:3],
                            }
                            for t, d in (rd.get("detected_technologies") or {}).items()
                        ],
                        key=lambda x: (x.get("confidence") or 0),
                        reverse=True,
                    )[:15],
                }
                for rd in (tech_stack_data.get("repo_details", []) or [])[:per_repo_limit]
            ],
        },
    )

    resume_skills = resume_data.get('skills') or []
    detected_skills = tech_stack_data.get('detected_skills') or {}

    if resume_skills:
        skill_matcher = SkillMatcher()
        matching_results = skill_matcher.match(resume_skills, detected_skills)

        _print_stage(
            "Skill matching completed",
            {
                "statistics": matching_results.get("statistics", {}),
                "matched_sample": (matching_results.get("matched_skills", []) or [])[:10],
                "missing_sample": (matching_results.get("missing_skills", []) or [])[:10],
                "extra_sample": (matching_results.get("extra_skills", []) or [])[:10],
            },
        )
    else:
        matching_results = _build_skipped_matching_results('No resume skills provided for matching')
        matching_results['statistics']['total_github_skills'] = len(detected_skills)
        _print_stage(
            "Skill matching skipped",
            {
                "reason": matching_results['statistics'].get('skip_reason'),
                "statistics": matching_results.get("statistics", {}),
            },
        )

    code_quality_analyzer = RepositoryQualityAnalyzer(github_service)
    code_quality_data = code_quality_analyzer.analyze_code_quality(
        github_data['repositories'],
        github_data['profile']['login']
    )

    _print_stage(
        "Code quality analyzed",
        {
            "overall_score": code_quality_data.get("overall_score"),
            "grade": code_quality_data.get("grade"),
            "repositories_analyzed": code_quality_data.get("repositories_analyzed"),
            "metrics": code_quality_data.get("metrics", {}),
            "scoring_model": code_quality_data.get("scoring_model", {}),
            "per_repo": [
                {
                    "repo": r.get("name"),
                    "score": r.get("score"),
                    "grade": r.get("grade"),
                    "language": r.get("language"),
                    "stars": r.get("stars"),
                    "evidence": {
                        "has_readme": (r.get("evidence") or {}).get("has_readme"),
                        # "has_tests": (r.get("evidence") or {}).get("has_tests"),
                        # "has_ci_cd": (r.get("evidence") or {}).get("has_ci_cd"),
                        # "has_license": (r.get("evidence") or {}).get("has_license"),
                        "has_dependency_manifest": (r.get("evidence") or {}).get("has_dependency_manifest"),
                        "commit_frequency": (r.get("evidence") or {}).get("commit_frequency"),
                        "commit_message_quality": (r.get("evidence") or {}).get("commit_message_quality"),
                        "code_quality_available": (r.get("evidence") or {}).get("code_quality_available"),
                    },
                    "scores": r.get("scores"),
                }
                for r in (code_quality_data.get("detailed_analysis", []) or [])[:per_repo_limit]
            ],
        },
    )

    contribution_analyzer = ContributionAnalyzer(github_service)
    contribution_data = contribution_analyzer.analyze_contributions(
        github_data['repositories'],
        github_data['profile']['login']
    )

    _print_stage(
        "Contributions analyzed",
        {
            "summary": contribution_data.get("summary", {}),
            "commit_activity": contribution_data.get("commit_activity", {}),
            "streak": contribution_data.get("contribution_streak", {}),
            "top_repositories": (contribution_data.get("top_repositories", []) or [])[:per_repo_limit],
            "contributions_to_others": (contribution_data.get("contributions_to_others", {}) or {}).get("contributions", [])[:per_repo_limit],
        },
    )

    scoring_engine = ScoringEngine()
    scores = scoring_engine.calculate_scores(
        github_data,
        tech_stack_data,
        matching_results,
        code_quality_data,
        contribution_data
    )

    _print_stage("Scores calculated", scores)

    # Consolidated per-repo view across analyses.
    tech_by_repo = {r.get("name"): r for r in (tech_stack_data.get("repo_details", []) or []) if r.get("name")}
    quality_by_repo = {r.get("name"): r for r in (code_quality_data.get("detailed_analysis", []) or []) if r.get("name")}
    contrib_by_repo = {
        r.get("name"): r
        for r in ((contribution_data.get("owned_repositories", {}) or {}).get("repo_details", []) or [])
        if r.get("name")
    }

    combined = []
    for repo in (github_data.get("repositories", []) or [])[:per_repo_limit]:
        name = repo.get("name")
        tech = tech_by_repo.get(name, {})
        qual = quality_by_repo.get(name, {})
        cont = contrib_by_repo.get(name, {})

        detected = list((tech.get("detected_technologies") or {}).keys())
        combined.append(
            {
                "repo": name,
                "stars": repo.get("stars"),
                "language": repo.get("language"),
                "updated_at": repo.get("updated_at"),
                "detected_tech_sample": detected[:12],
                "quality_score": qual.get("score"),
                "quality_grade": qual.get("grade"),
                "commit_stats": {
                    "user_commits": cont.get("user_commits"),
                    "total_commits": cont.get("total_commits"),
                    "ownership_percentage": cont.get("ownership_percentage"),
                    "commit_message_quality": cont.get("commit_message_quality"),
                    "is_active": cont.get("is_active"),
                },
            }
        )

    _print_stage("Per-repository consolidated summary", combined)

    report_generator = ReportGenerator()
    report = report_generator.generate({
        'candidate': resume_data,
        'github': github_data,
        'tech_stack': tech_stack_data,
        'matching': matching_results,
        'scores': scores,
        'code_quality': code_quality_data,
        'contributions': contribution_data
    })

    _print_stage(
        "Final report generated (high-level)",
        {
            "candidate": report.get("candidateSummary", {}),
            "scoringAnalysis": report.get("scoringAnalysis", {}),
            "recommendation": report.get("recommendation", {}),
            "codeQualityReport": {
                "overallScore": (report.get("codeQualityReport", {}) or {}).get("overallScore"),
                "grade": (report.get("codeQualityReport", {}) or {}).get("grade"),
            },
            "contributionReport": (report.get("contributionReport", {}) or {}).get("summary", {}),
        },
    )

    # Save deep analysis HTML artifact locally from the same in-pipeline data.
    try:
        artifact_path = _save_deep_scoring_report(
            report,
            scores,
            code_quality_data,
            contribution_data,
            matching_results,
            tech_stack_data,
            github_data,
        )
        _print_stage("Deep scoring report saved locally", {"path": artifact_path})
    except Exception as save_error:
        _print_stage("Deep scoring report save failed", {"error": str(save_error)})

    return report, resume_data


def process_github_username(username):
    """Run full analysis pipeline using only a GitHub username (no resume file)."""
    github_username = (username or '').strip()
    if not github_username:
        raise MissingGithubUrl('No GitHub username provided for direct analysis.')

    # Minimal resume-like payload so downstream pipeline remains unchanged.
    pseudo_resume = {
        'name': None,
        'email': None,
        'phone': None,
        'github_url': github_username,
        'skills': []
    }

    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"direct_{os.urandom(6).hex()}.json")
    try:
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(pseudo_resume, f)

        # Reuse the same pipeline by bypassing parser stage manually.
        # Inline path keeps behavior consistent with process_resume_file internals.
        report, _ = process_resume_file(temp_path, github_username_fallback=github_username)
        return report
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def build_summary_row(report, index):
    scoring = report.get('scoringAnalysis', {})
    breakdown = scoring.get('scoreBreakdown', {})
    candidate = report.get('candidateSummary', {})
    matching = report.get('skillMatchingReport', {}).get('summary', {})
    code_quality = report.get('codeQualityReport', {})
    contributions = report.get('contributionReport', {}).get('summary', {})

    code_quality_metrics = code_quality.get('metrics', {})

    return {
        'id': index,
        'name': candidate.get('name') or 'Unknown',
        'githubUsername': candidate.get('githubUsername') or '',
        'overallScore': scoring.get('overallScore', 0),
        'rating': scoring.get('rating', 'N/A'),
        'skillAuthenticity': breakdown.get('skillAuthenticity', 0),
        'codeQualityScore': breakdown.get('codeQuality', 0),
        'codeHealthScore': code_quality_metrics.get('codeHealthScore'),
        'commitActivityScore': breakdown.get('commitActivity', 0),
        'techStackScore': breakdown.get('techStack', 0),
        'profileSignalScore': breakdown.get('profileSignal', 0),
        'codeQualityGrade': code_quality.get('grade', 'N/A'),
        'skillMatchPercentage': matching.get('matchPercentage', 0),
        'totalCommits': contributions.get('total_commits', contributions.get('totalCommits', 0)),
    }


def build_aggregates(rows):
    if not rows:
        return {'avgScore': 0, 'count': 0}
    total = sum(r.get('overallScore', 0) for r in rows)
    count = len(rows)
    return {
        'avgScore': round(total / count, 2) if count else 0,
        'count': count
    }

app = Flask(__name__)
CORS(app, origins=os.getenv('CLIENT_URL', 'http://localhost:5173'), supports_credentials=True)

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'docx'}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS




@app.route('/api/analysis/upload', methods=['POST'])
def analyze_resume():
    try:
        github_username = (request.form.get('github_username') or '').strip()
        has_resume = 'resume' in request.files and request.files['resume'].filename != ''

        if not has_resume and not github_username:
            return jsonify({'success': False, 'error': 'Provide either a resume file or a GitHub username'}), 400

        # Direct username mode (no resume file uploaded).
        if not has_resume and github_username:
            report = process_github_username(github_username)
            print(f"Direct GitHub analysis completed for: {github_username}")
            return jsonify({'success': True, 'report': report})

        file = request.files['resume']

        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file type. Only PDF and DOCX files are allowed.'}), 400

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{os.urandom(8).hex()}_{filename}")
        file.save(filepath)

        print(f"Processing resume: {filename}")

        try:
            report, resume_data = process_resume_file(filepath, github_username_fallback=github_username)
            print("Report generated successfully")
            return jsonify({'success': True, 'report': report})
        except MissingGithubUrl as e:
            data = e.resume_data or {}
            return jsonify({
                'success': False,
                'error': str(e),
                'debug': {
                    'name': data.get('name'),
                    'email': data.get('email'),
                    'skillsFound': len(data.get('skills', [])),
                }
            }), 400

        finally:
            # Clean up uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)

    except Exception as e:
        print(f"Analysis error: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'details': traceback.format_exc() if os.getenv('FLASK_ENV') == 'development' else None
        }), 500


@app.route('/api/analysis/bulk-upload', methods=['POST'])
def analyze_bulk_resumes():
    """Accept a zip of resumes, analyze each, and return summary + per-candidate reports."""
    temp_dir = tempfile.mkdtemp()
    try:
        if 'resumes' not in request.files:
            return jsonify({'success': False, 'error': 'No zip file uploaded'}), 400

        zip_file = request.files['resumes']
        if zip_file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        if not zip_file.filename.lower().endswith('.zip'):
            return jsonify({'success': False, 'error': 'Invalid file type. Only ZIP is allowed for bulk uploads.'}), 400

        zip_path = os.path.join(temp_dir, secure_filename(zip_file.filename))
        zip_file.save(zip_path)

        extract_dir = os.path.join(temp_dir, 'extracted')
        os.makedirs(extract_dir, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)

        rows = []
        reports = []
        failures = []
        idx = 1

        for root, _, files in os.walk(extract_dir):
            for fname in files:
                if not allowed_file(fname):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    report, _ = process_resume_file(fpath)
                    rows.append(build_summary_row(report, idx))
                    reports.append(report)
                    idx += 1
                except MissingGithubUrl as e:
                    failures.append({'file': fname, 'error': str(e)})
                except Exception as e:
                    failures.append({'file': fname, 'error': str(e)})

        aggregates = build_aggregates(rows)

        return jsonify({
            'success': True,
            'summary': {
                'rows': rows,
                'aggregates': aggregates,
                'processed': len(rows),
                'failed': len(failures)
            },
            'reports': reports,
            'failures': failures
        })
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@app.route('/api/analysis/debug-parse', methods=['POST'])
def debug_parse():
    try:
        if 'resume' not in request.files:
            return jsonify({'success': False, 'error': 'No resume file uploaded'}), 400

        file = request.files['resume']
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{os.urandom(8).hex()}_{filename}")
        file.save(filepath)

        try:
            resume_parser = ResumeParser()
            resume_data = resume_parser.parse(filepath)

            return jsonify({
                'success': True,
                'debug': {
                    'name': resume_data.get('name'),
                    'email': resume_data.get('email'),
                    'phone': resume_data.get('phone'),
                    'githubUrl': resume_data.get('github_url'),
                    'skillsFound': resume_data.get('skills', []),
                }
            })
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/analysis/test-github/<username>', methods=['GET'])
def test_github(username):
    try:
        github_service = GitHubService()
        github_data = github_service.fetch_user_data(username)
        return jsonify({'success': True, 'data': github_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/analysis/download-report', methods=['POST'])
def download_report():
    try:
        report_data = request.get_json()
        if not report_data:
            return jsonify({'success': False, 'error': 'No report data provided'}), 400

        report_generator = ReportGenerator()
        is_html = 'html' in report_data

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            pdf_path = tmp_file.name

        if is_html:
            report_generator.generate_pdf_from_html(report_data['html'], pdf_path)
        else:
            report_generator.generate_pdf_report(report_data, pdf_path)

        candidate_name = report_data.get('candidateSummary', {}).get('name') or report_data.get('name') or 'candidate'
        safe_name = "".join(c for c in candidate_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        
        response = send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'{safe_name}_analysis.pdf'
        )
        
        @response.call_on_close
        def cleanup():
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        
        return response

    except Exception as e:
        print(f"PDF generation error: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'success': False, 'error': 'File size exceeds 5MB limit'}), 413


@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    print(f"Server running on http://localhost:{port}")
    print(f"Environment: {os.getenv('FLASK_ENV', 'production')}")
    print(f"GitHub Token: {'Configured' if os.getenv('GITHUB_TOKEN') else 'Missing'}")
    app.run(host='0.0.0.0', port=port, debug=debug)
