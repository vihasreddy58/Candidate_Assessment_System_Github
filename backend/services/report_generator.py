from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from playwright.sync_api import sync_playwright
from reportlab.lib.colors import HexColor, black, green, red, blue, gray
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.legends import Legend


class ReportGenerator:
    def __init__(self):
        self.report_version = '1.0.0'

    def generate_pdf_report(self, report_data, output_path):
        """
        Existing structured PDF generator (ReportLab). Deprecated for UI parity.
        """
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=40,
            bottomMargin=40
        )

        styles = getSampleStyleSheet()
        story = []

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=HexColor('#667eea'),
            alignment=1,
            spaceAfter=10
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=HexColor('#333333'),
            spaceAfter=8
        )

        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=9,
            textColor=black,
            spaceAfter=4
        )

        # Extract data
        candidate = report_data.get('candidateSummary', {})
        github = report_data.get('githubProfile', {})
        matching = report_data.get('skillMatchingReport', {})
        scores = report_data.get('scoringAnalysis', {})

        # Title
        story.append(Paragraph('GitHub Hiring Analysis Report', title_style))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 
                               ParagraphStyle('DateStyle', parent=normal_style, alignment=1, textColor=gray)))
        story.append(Spacer(1, 20))

        # Candidate Info
        story.append(Paragraph('Candidate Information', heading_style))
        candidate_name = candidate.get('name', 'N/A')
        candidate_email = candidate.get('email', 'N/A')
        github_username = candidate.get('githubUsername', 'N/A')
        
        story.append(Paragraph(f"<b>Name:</b> {candidate_name}", normal_style))
        story.append(Paragraph(f"<b>Email:</b> {candidate_email}", normal_style))
        story.append(Paragraph(f"<b>GitHub:</b> @{github_username}", normal_style))
        story.append(Spacer(1, 15))

        # GitHub Profile
        story.append(Paragraph('GitHub Profile Summary', heading_style))
        stats = github.get('statistics', {})
        activity = github.get('activity', {})
        overview = github.get('overview', {})
        
        story.append(Paragraph(f"<b>Repositories:</b> {stats.get('publicRepositories', 0)} | "
                               f"<b>Followers:</b> {stats.get('followers', 0)} | "
                               f"<b>Account Age:</b> {overview.get('accountAge', 'N/A')}", normal_style))
        story.append(Paragraph(f"<b>Total Stars:</b> {activity.get('totalStars', 0)} | "
                               f"<b>Active Repos:</b> {activity.get('activeRepositories', 0)}", normal_style))
        story.append(Spacer(1, 15))

        # Skills Summary
        story.append(Paragraph('Skills Analysis', heading_style))
        summary = matching.get('summary', {})
        story.append(Paragraph(f"<b>Resume Skills:</b> {summary.get('totalResumeSkills', 0)} | "
                               f"<b>Matched:</b> {summary.get('matchedSkills', 0)} ({summary.get('matchPercentage', 0)}%) | "
                               f"<b>Missing:</b> {summary.get('missingSkills', 0)}", normal_style))
        story.append(Spacer(1, 10))

        # Pie Chart for Skills
        matched_count = summary.get('matchedSkills', 0)
        missing_count = summary.get('missingSkills', 0)
        extra_count = summary.get('extraSkills', 0)
        
        if matched_count + missing_count + extra_count > 0:
            drawing = Drawing(400, 150)
            pie = Pie()
            pie.x = 100
            pie.y = 10
            pie.width = 120
            pie.height = 120
            pie.data = [matched_count, missing_count, extra_count]
            pie.labels = [f'Verified ({matched_count})', f'Not Verified ({missing_count})', f'Extra Found ({extra_count})']
            pie.slices.strokeWidth = 0.5
            pie.slices[0].fillColor = HexColor('#10b981')  # Green for verified
            pie.slices[1].fillColor = HexColor('#ef4444')  # Red for missing
            pie.slices[2].fillColor = HexColor('#3b82f6')  # Blue for extra
            pie.slices[0].popout = 5
            
            # Add legend
            legend = Legend()
            legend.x = 260
            legend.y = 80
            legend.dx = 8
            legend.dy = 8
            legend.fontName = 'Helvetica'
            legend.fontSize = 8
            legend.boxAnchor = 'w'
            legend.columnMaximum = 3
            legend.strokeWidth = 0.5
            legend.strokeColor = gray
            legend.deltax = 75
            legend.deltay = 10
            legend.autoXPadding = 5
            legend.colorNamePairs = [
                (HexColor('#10b981'), f'Verified: {matched_count}'),
                (HexColor('#ef4444'), f'Not Verified: {missing_count}'),
                (HexColor('#3b82f6'), f'Extra Found: {extra_count}')
            ]
            
            drawing.add(pie)
            drawing.add(legend)
            story.append(drawing)
            story.append(Spacer(1, 10))

        # Matched Skills
        matched_skills = matching.get('matchedSkills', [])
        if matched_skills:
            story.append(Paragraph('<font color="green"><b>Verified Skills:</b></font>', normal_style))
            matched_text = ', '.join([f"{s.get('resumeSkill', '')} ({int(s.get('confidence', 0))}%)" 
                                      for s in matched_skills[:12]])
            story.append(Paragraph(matched_text, normal_style))
            if len(matched_skills) > 12:
                story.append(Paragraph(f"+ {len(matched_skills) - 12} more", normal_style))

        # Missing Skills
        missing_skills = matching.get('missingSkills', [])
        if missing_skills:
            story.append(Spacer(1, 8))
            story.append(Paragraph('<font color="red"><b>Not Verified:</b></font>', normal_style))
            missing_text = ', '.join([s.get('skill', '') for s in missing_skills[:10]])
            story.append(Paragraph(missing_text, normal_style))
            if len(missing_skills) > 10:
                story.append(Paragraph(f"+ {len(missing_skills) - 10} more", normal_style))

        # Extra Skills
        extra_skills = matching.get('extraSkills', [])
        if extra_skills:
            story.append(Spacer(1, 8))
            story.append(Paragraph('<font color="blue"><b>Additional Skills Found:</b></font>', normal_style))
            for skill in extra_skills[:6]:
                skill_name = skill.get('skill', '')
                repos = ', '.join(skill.get('repositories', [])[:2]) or 'GitHub'
                story.append(Paragraph(f"  - {skill_name} (Found in: {repos})", normal_style))

        story.append(Spacer(1, 15))

        # Assessment Score
        story.append(Paragraph('Assessment', heading_style))
        overall_score = scores.get('overallScore', 0)
        rating = scores.get('rating', 'N/A')

        story.append(Paragraph(f"<b>Overall Score:</b> {overall_score}/100 ({rating})", normal_style))
        story.append(Spacer(1, 10))

        # Strengths
        strengths = scores.get('strengths', [])
        if strengths:
            story.append(Paragraph('<font color="green"><b>Strengths:</b></font>', normal_style))
            for s in strengths:
                desc = s.get('description', s.get('area', ''))
                story.append(Paragraph(f"  - {desc}", normal_style))

        # Footer
        story.append(Spacer(1, 30))
        story.append(Paragraph('GitHub Hiring Analysis System', 
                               ParagraphStyle('Footer', parent=normal_style, alignment=1, textColor=gray, fontSize=7)))

        doc.build(story)

    def generate_pdf_from_html(self, html_string, output_path):
        """
        Render the dashboard HTML into a PDF so styling matches the UI.
        Uses Playwright (Chromium) for full HTML/CSS fidelity.
        """
        

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1240, "height": 1754})
            page.set_content(html_string, wait_until="load")
            page.pdf(
                path=output_path,
                format="A4",
                print_background=True,
                margin={"top": "16mm", "right": "14mm", "bottom": "16mm", "left": "14mm"}
            )
            browser.close()

    def generate(self, data):
        candidate = data['candidate']
        github = data['github']
        tech_stack = data['tech_stack']
        matching = data['matching']
        scores = data['scores']
        code_quality = data.get('code_quality', {})
        contributions = data.get('contributions', {})

        print("Generating comprehensive report...")

        report = {
            'metadata': {
                'generatedAt': datetime.utcnow().isoformat(),
                'reportVersion': self.report_version,
                'analysisType': 'GitHub Hiring Analysis'
            },
            'candidateSummary': self._generate_candidate_summary(candidate, github),
            'githubProfile': self._generate_github_profile_summary(github),
            'technicalAnalysis': self._generate_technical_analysis(tech_stack, matching),
            'skillMatchingReport': self._generate_skill_matching_report(matching),
            'repositoryInsights': self._generate_repository_insights(github, tech_stack),
            'codeQualityReport': self._generate_code_quality_report(code_quality),
            'contributionReport': self._generate_contribution_report(contributions),
            'scoringAnalysis': self._generate_scoring_analysis(scores),
            'recommendation': self._generate_recommendation(scores, matching, github),
            'detailedMetrics': self._generate_detailed_metrics(github, tech_stack, matching)
        }

        return report

    def _generate_candidate_summary(self, candidate, github):
        return {
            'name': candidate.get('name') or github['profile'].get('name') or 'Unknown',
            'email': candidate.get('email') or github['profile'].get('email'),
            'phone': candidate.get('phone'),
            'githubUsername': github['profile']['login'],
            'githubUrl': f"https://github.com/{github['profile']['login']}",
            'location': github['profile'].get('location'),
            'bio': github['profile'].get('bio'),
            'company': github['profile'].get('company'),
            'resumeSkillsCount': len(candidate.get('skills', []))
        }

    def _generate_github_profile_summary(self, github):
        profile = github['profile']
        contribution_stats = github.get('contribution_stats', {})
        
        return {
            'overview': {
                'username': profile['login'],
                'name': profile.get('name'),
                'accountAge': profile.get('account_age', 'Unknown'),
                'avatarUrl': profile.get('avatar_url')
            },
            'statistics': {
                'publicRepositories': profile.get('public_repos', 0),
                'publicGists': profile.get('public_gists', 0),
                'followers': profile.get('followers', 0),
                'following': profile.get('following', 0)
            },
            'activity': {
                'totalStars': contribution_stats.get('total_stars', 0),
                'totalForks': contribution_stats.get('total_forks', 0),
                'activeRepositories': contribution_stats.get('active_repositories', 0),
                'recentActivity': {
                    'isActive': contribution_stats.get('active_repositories', 0) > 2
                }
            },
            'languageDistribution': github.get('language_stats', {})
        }

    def _generate_technical_analysis(self, tech_stack, matching):
        detected_skills = tech_stack.get('detected_skills', {})
        
        categories = {
            'languages': [],
            'frameworks': [],
            'databases': [],
            'tools': [],
            'cloud': []
        }

        for skill, data in detected_skills.items():
            skill_type = data.get('type', 'other')
            if skill_type == 'language':
                categories['languages'].append(skill)
            elif skill_type in ['framework', 'library']:
                categories['frameworks'].append(skill)
            elif skill_type == 'database':
                categories['databases'].append(skill)
            else:
                categories['tools'].append(skill)

        return {
            'detectedSkills': detected_skills,
            'skillsByCategory': categories,
            'totalDetected': len(detected_skills),
            'repositoriesAnalyzed': tech_stack.get('total_repos_analyzed', 0)
        }

    def _generate_skill_matching_report(self, matching):
        match_percentage = matching['statistics'].get('match_percentage', 0)
        authenticity_score = matching['statistics'].get('authenticity_score', 0)
        skipped = bool(matching['statistics'].get('skipped'))
        skip_reason = matching['statistics'].get('skip_reason')
        # Keep authenticityScore consistent with matchPercentage (never lower).
        display_authenticity = max(float(authenticity_score or 0), float(match_percentage or 0))
        return {
            'summary': {
                'totalResumeSkills': matching['statistics']['total_resume_skills'],
                'totalGithubSkills': matching['statistics']['total_github_skills'],
                'matchedSkills': matching['statistics']['matched_count'],
                'missingSkills': matching['statistics']['missing_count'],
                'extraSkills': matching['statistics']['extra_count'],
                'matchPercentage': matching['statistics']['match_percentage'],
                'authenticityScore': round(display_authenticity, 2),
                'skipped': skipped,
                'skipReason': skip_reason,
            },
            'matchedSkills': [
                {
                    'resumeSkill': s['skill'],
                    'githubSkill': s.get('github_skill', s['skill']),
                    'confidence': round(s.get('confidence', 0), 2),
                    'usageFrequency': s.get('usage_frequency', 0),
                    'repositories': s.get('repositories', []),
                    'matchType': s.get('match_type', 'exact')
                }
                for s in matching['matched_skills']
            ],
            'missingSkills': [
                {
                    'skill': s['skill'],
                    'reason': s.get('reason', 'Not found'),
                    'category': s.get('category', 'other'),
                    'severity': s.get('severity', 'medium')
                }
                for s in matching['missing_skills']
            ],
            'extraSkills': [
                {
                    'skill': s['skill'],
                    'confidence': s.get('confidence', 0),
                    'usageFrequency': s.get('usage_frequency', 0),
                    'repositories': s.get('repositories', []),
                    'category': s.get('category', 'other'),
                    'recommendation': s.get('recommendation', '')
                }
                for s in matching['extra_skills']
            ]
        }

    def _generate_repository_insights(self, github, tech_stack):
        repos = github.get('repositories', [])
        repo_details = tech_stack.get('repo_details', [])

        top_repos = sorted(repos, key=lambda x: x.get('stars', 0), reverse=True)[:10]
        
        # Calculate activity pattern based on repo update dates
        from datetime import datetime, timedelta
        now = datetime.now()
        very_recent = 0  # Last 30 days
        recent = 0  # Last 90 days
        moderate = 0  # Last 180 days
        old = 0  # Older
        
        for repo in repos:
            updated_str = repo.get('updated_at') or repo.get('pushed_at')
            if updated_str:
                try:
                    updated = datetime.fromisoformat(updated_str.replace('Z', '+00:00'))
                    days_ago = (now.replace(tzinfo=updated.tzinfo) - updated).days
                    if days_ago <= 30:
                        very_recent += 1
                    elif days_ago <= 90:
                        recent += 1
                    elif days_ago <= 180:
                        moderate += 1
                    else:
                        old += 1
                except:
                    old += 1
        
        total = len(repos) or 1
        if very_recent / total > 0.3:
            activity_level = 'Very Active'
        elif (very_recent + recent) / total > 0.3:
            activity_level = 'Active'
        elif (very_recent + recent + moderate) / total > 0.3:
            activity_level = 'Moderate'
        else:
            activity_level = 'Low'

        return {
            'totalRepositories': len(repos),
            'analyzedRepositories': len(repo_details),
            'topRepositories': [
                {
                    'name': repo['name'],
                    'description': repo.get('description'),
                    'language': repo.get('language'),
                    'stars': repo.get('stars', 0),
                    'forks': repo.get('forks', 0),
                    'url': repo.get('url'),
                    'lastUpdated': repo.get('updated_at'),
                    'detectedTechnologies': next(
                        (r.get('detected_technologies', {}) for r in repo_details if r['name'] == repo['name']),
                        {}
                    )
                }
                for repo in top_repos
            ],
            'activityPattern': {
                'veryRecent': very_recent,
                'recent': recent,
                'moderate': moderate,
                'old': old,
                'activityLevel': activity_level
            }
        }

    def _generate_code_quality_report(self, code_quality):
        """Generate repository quality analysis report"""
        if not code_quality:
            return {
                'overallScore': 0,
                'grade': 'N/A',
                'gradeLabel': 'Not Analyzed',
                'repositoriesAnalyzed': 0,
                'metrics': {},
                'categoryScores': {},
                'repositoryDetails': [],
                'strengths': [],
                'weaknesses': [],
                'suggestions': []
            }
        
        metrics = code_quality.get('metrics', {})
        scoring_model = code_quality.get('scoring_model', {})
        avg_code_health = metrics.get('avg_code_health_score')
        code_health_enabled = bool(scoring_model.get('code_health_enabled', False))
        code_health_language = metrics.get('code_health_language')
        code_health_languages = metrics.get('code_health_languages')
        
        return {
            'overallScore': code_quality.get('overall_score', 0),
            'grade': code_quality.get('grade', 'N/A'),
            'gradeLabel': code_quality.get('grade_label', 'Unknown'),
            'repositoriesAnalyzed': code_quality.get('repositories_analyzed', 0),
            'metrics': {
                'reposWithReadme': metrics.get('repos_with_readme', 0),
                # 'reposWithTests': metrics.get('repos_with_tests', 0),
                # 'reposWithCiCd': metrics.get('repos_with_ci_cd', 0),
                #'reposWithReadinessSignals': metrics.get('repos_with_readiness_signals', 0),
                #'reposWithLicense': metrics.get('repos_with_license', 0),
                'reposWithDocs': metrics.get('repos_with_docs', 0),
                'readmePercentage': metrics.get('readme_percentage', 0),
                #'readinessPercentage': metrics.get('readiness_percentage', metrics.get('testing_percentage', 0)),
                #'testingPercentage': metrics.get('testing_percentage', metrics.get('readiness_percentage', 0)),
                #'ciCdPercentage': metrics.get('ci_cd_percentage', 0),
                'codeHealthEnabled': code_health_enabled,
                'codeHealthAvailable': avg_code_health is not None,
                'codeHealthScore': avg_code_health,
                'codeHealthLanguage': code_health_language,
                'codeHealthLanguages': code_health_languages if isinstance(code_health_languages, list) else [],
                'codeHealthReposAnalyzed': metrics.get('code_health_repos_analyzed', 0),
                'codeHealthFilesAnalyzed': metrics.get('code_health_files_analyzed', 0)
            },
            'categoryScores': {
                **{
                    'documentation': metrics.get('avg_documentation_score', 0),
                    #'readiness': metrics.get('avg_testing_score', 0),
                    #'testing': metrics.get('avg_testing_score', 0),
                    'codeOrganization': metrics.get('avg_code_organization_score', 0),
                    #'maintainability': metrics.get('avg_maintainability_score', 0),
                    'commitQuality': metrics.get('avg_commit_quality_score', 0),
                },
                **({'codeHealth': (avg_code_health if avg_code_health is not None else 0)} if code_health_enabled else {})
            },
            'repositoryDetails': [],
            'strengths': [
                {
                    'area': s.get('area', ''),
                    'description': s.get('description', '')
                }
                for s in code_quality.get('strengths', [])
            ],
            'weaknesses': [
                {
                    'area': w.get('area', ''),
                    'description': w.get('description', '')
                }
                for w in code_quality.get('weaknesses', [])
            ],
            'suggestions': [
                {
                    'category': s.get('category', ''),
                    'priority': s.get('priority', 'medium'),
                    'suggestion': s.get('suggestion', ''),
                    'impact': s.get('impact', '')
                }
                for s in code_quality.get('suggestions', [])
            ]
        }

    def _generate_contribution_report(self, contributions):
        """Generate contribution analysis report"""
        if not contributions:
            return {
                'summary': {
                    'totalCommits': 0,
                    'ownedRepoCommits': 0,
                    'forkContributions': 0,
                    'reposWithCommits': 0,
                    'isActiveContributor': False
                },
                'topRepositories': [],
                'contributionsToOthers': [],
                'commitActivity': {},
                'streak': {}
            }
        
        summary = contributions.get('summary', {})
        owned = contributions.get('owned_repositories', {})
        forks = contributions.get('contributions_to_others', {})
        activity = contributions.get('commit_activity', {})
        streak = contributions.get('contribution_streak', {})
        top_repos = contributions.get('top_repositories', [])
        
        return {
            'summary': {
                'totalCommits': summary.get('total_commits', 0),
                'ownedRepoCommits': summary.get('owned_repo_commits', 0),
                'forkContributions': summary.get('fork_contributions', 0),
                'reposWithCommits': summary.get('repos_with_commits', 0),
                'isActiveContributor': summary.get('active_contributor', False)
            },
            'topRepositories': [
                {
                    'name': repo.get('name', ''),
                    'url': repo.get('url', ''),
                    'language': repo.get('language', 'Unknown'),
                    'stars': repo.get('stars', 0),
                    'userCommits': repo.get('user_commits', 0),
                    'totalCommits': repo.get('total_commits', 0),
                    'ownershipPercentage': repo.get('ownership_percentage', 0),
                    'lastCommit': repo.get('last_commit'),
                    'commitMessageQuality': repo.get('commit_message_quality', 'unknown'),
                    'isActive': repo.get('is_active', False)
                }
                for repo in top_repos
            ],
            'contributionsToOthers': [
                {
                    'name': contrib.get('name', ''),
                    'url': contrib.get('url', ''),
                    'originalRepo': contrib.get('original_repo', ''),
                    'language': contrib.get('language', 'Unknown'),
                    'commits': contrib.get('commits', 0),
                    'lastContribution': contrib.get('last_contribution'),
                    'contributionType': contrib.get('contribution_type', 'fork')
                }
                for contrib in forks.get('contributions', [])
            ],
            'isOpenSourceContributor': forks.get('is_open_source_contributor', False),
            'commitActivity': {
                'monthlyActivity': activity.get('monthly_activity', {}),
                'dailyDistribution': activity.get('daily_distribution', {}),
                'mostActiveDay': activity.get('most_active_day', 'Unknown'),
                'totalRecentCommits': activity.get('total_recent_commits', 0)
            },
            'streak': {
                'currentStreakMonths': streak.get('current_streak_months', 0),
                'activeMonths': streak.get('active_months', 0),
                'isConsistent': streak.get('is_consistent', False)
            }
        }

    def _generate_scoring_analysis(self, scores):
        breakdown = scores.get('breakdown', {})
        skill_auth = breakdown.get('skill_authenticity', 0)
        overall = scores['overall']
        return {
            'overallScore': overall,
            'rating': scores['rating'],
            'scoreBreakdown': {
                'skillAuthenticity': skill_auth,
                'codeQuality': breakdown.get('code_quality', 0),
                'commitActivity': breakdown.get('commit_activity', 0),
                'techStack': breakdown.get('tech_stack', 0),
                'profileSignal': breakdown.get('profile_signal', 0)
            }
        }

    def _generate_recommendation(self, scores, matching, github):
        overall_score = scores['overall']
        match_percentage = matching['statistics']['match_percentage']
        matching_skipped = bool(matching['statistics'].get('skipped'))

        if overall_score >= 80:
            decision = 'Strongly Recommend'
            confidence = 'High'
        elif overall_score >= 65:
            decision = 'Recommend'
            confidence = 'Medium-High'
        elif overall_score >= 50:
            decision = 'Consider with Review'
            confidence = 'Medium'
        elif overall_score >= 35:
            decision = 'Review Required'
            confidence = 'Low'
        else:
            decision = 'Not Recommended'
            confidence = 'Very Low'

        reasoning = []
        if matching_skipped:
            reasoning.append("Skill matching was skipped because resume skills were not provided")
        elif match_percentage >= 70:
            reasoning.append(f"High skill match rate ({match_percentage}%) indicates authentic technical claims")
        elif match_percentage >= 50:
            reasoning.append(f"Moderate skill match ({match_percentage}%) with room for improvement")
        else:
            reasoning.append(f"Low skill match ({match_percentage}%) - many claimed skills not verified")

        if len(matching['matched_skills']) > 5:
            reasoning.append(f"{len(matching['matched_skills'])} skills verified through GitHub activity")

        key_highlights = []
        avg_confidence = 0
        if matching['matched_skills']:
            avg_confidence = sum(s.get('confidence', 0) for s in matching['matched_skills']) / len(matching['matched_skills'])
            if avg_confidence >= 80:
                key_highlights.append("High confidence in verified skills")

        if matching['extra_skills']:
            key_highlights.append(f"{len(matching['extra_skills'])} additional skills discovered")

        return {
            'decision': decision,
            'confidence': confidence,
            'reasoning': reasoning,
            'keyHighlights': key_highlights,
            'skillMatchingSkipped': matching_skipped,
        }

    def _generate_detailed_metrics(self, github, tech_stack, matching):
        return {
            'skillMetrics': {
                'totalVerified': matching['statistics']['matched_count'],
                'verificationRate': matching['statistics']['match_percentage'],
                'averageConfidence': round(
                    sum(s.get('confidence', 0) for s in matching['matched_skills']) / len(matching['matched_skills']), 2
                ) if matching['matched_skills'] else 0
            },
            'githubMetrics': {
                'repositoryCount': len(github.get('repositories', [])),
                'analysisDepth': tech_stack.get('total_repos_analyzed', 0),
                'technologiesDetected': len(tech_stack.get('detected_skills', {}))
            }
        }
