##working on this 
##Not included in final code
from datetime import datetime, timedelta
import re
from collections import defaultdict


class CodeAnalyzer:
    """Analyzes code quality and contribution patterns from GitHub data"""
    
    def __init__(self):
        # File extensions for different categories
        self.code_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', 
            '.cs', '.go', '.rb', '.php', '.swift', '.kt', '.rs', '.scala'
        }
        self.config_extensions = {'.json', '.yaml', '.yml', '.toml', '.xml', '.ini', '.env'}
        self.doc_extensions = {'.md', '.txt', '.rst', '.adoc'}
        
    def analyze_repository(self, repo_data, repo_stats):
        """Perform comprehensive analysis on a repository"""
        analysis = {
            'commit_analysis': self.analyze_commits(repo_stats.get('commits', [])),
            'contributor_analysis': self.analyze_contributors(repo_stats.get('contributors', [])),
            'language_analysis': self.analyze_languages(repo_stats.get('languages', {})),
            'project_maturity': self.assess_project_maturity(repo_data, repo_stats),
            'code_velocity': self.calculate_code_velocity(repo_stats.get('commits', [])),
            'quality_score': 0
        }
        
        # Calculate overall quality score
        analysis['quality_score'] = self.calculate_quality_score(analysis)
        
        return analysis
    
    def analyze_commits(self, commits):
        """Analyze commit patterns and quality"""
        if not commits:
            return {
                'total_count': 0,
                'user_commits': 0,
                'ownership_percentage': 0,
                'commit_frequency': 'None',
                'commit_quality': 0,
                'avg_message_length': 0,
                'recent_activity': False,
                'weekly_distribution': {}
            }
        
        user_commits = sum(1 for c in commits if c.get('is_user'))
        total_count = len(commits)
        ownership_pct = (user_commits / total_count * 100) if total_count > 0 else 0
        
        # Analyze commit message quality
        message_lengths = [len(c.get('message', '').split('\n')[0]) for c in commits]
        avg_message_length = sum(message_lengths) / len(message_lengths) if message_lengths else 0
        
        # Score commit message quality (good messages are 20-72 chars)
        good_messages = sum(1 for m in message_lengths if 20 <= m <= 72)
        commit_quality = (good_messages / len(message_lengths) * 100) if message_lengths else 0
        
        # Check recent activity (commits in last 30 days)
        recent_activity = False
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        for c in commits[:10]:
            try:
                commit_date = datetime.fromisoformat(c.get('date', '').replace('Z', '+00:00'))
                if commit_date.replace(tzinfo=None) > thirty_days_ago:
                    recent_activity = True
                    break
            except:
                pass
        
        # Determine commit frequency
        if total_count >= 50:
            frequency = 'High'
        elif total_count >= 20:
            frequency = 'Moderate'
        elif total_count >= 5:
            frequency = 'Low'
        else:
            frequency = 'Minimal'
        
        # Weekly distribution
        weekly_counts = defaultdict(int)
        for c in commits:
            try:
                commit_date = datetime.fromisoformat(c.get('date', '').replace('Z', '+00:00'))
                day_name = commit_date.strftime('%A')
                weekly_counts[day_name] += 1
            except:
                pass
        
        return {
            'total_count': total_count,
            'user_commits': user_commits,
            'ownership_percentage': round(ownership_pct, 1),
            'commit_frequency': frequency,
            'commit_quality': round(commit_quality, 1),
            'avg_message_length': round(avg_message_length, 1),
            'recent_activity': recent_activity,
            'weekly_distribution': dict(weekly_counts)
        }
    
    def analyze_contributors(self, contributors):
        """Analyze contribution distribution"""
        if not contributors:
            return {
                'total_contributors': 0,
                'is_solo_project': True,
                'contribution_share': 0,
                'is_primary_contributor': False
            }
        
        total_contributors = len(contributors)
        owner_data = next((c for c in contributors if c.get('is_owner')), None)
        total_contributions = sum(c.get('contributions', 0) for c in contributors)
        
        owner_contributions = owner_data.get('contributions', 0) if owner_data else 0
        contribution_share = (owner_contributions / total_contributions * 100) if total_contributions > 0 else 0
        
        # Is primary if they have majority of commits
        is_primary = contribution_share > 50
        
        return {
            'total_contributors': total_contributors,
            'is_solo_project': total_contributors == 1,
            'contribution_share': round(contribution_share, 1),
            'is_primary_contributor': is_primary,
            'collaboration_level': 'Team' if total_contributors > 2 else ('Pair' if total_contributors == 2 else 'Solo')
        }
    
    def analyze_languages(self, languages):
        """Analyze language usage and diversity"""
        if not languages:
            return {
                'primary_language': 'Unknown',
                'language_count': 0,
                'language_distribution': {},
                'is_polyglot': False
            }
        
        total_bytes = sum(languages.values())
        distribution = {
            lang: round(bytes_count / total_bytes * 100, 1)
            for lang, bytes_count in languages.items()
        } if total_bytes > 0 else {}
        
        # Sort by percentage
        sorted_langs = sorted(distribution.items(), key=lambda x: x[1], reverse=True)
        primary_language = sorted_langs[0][0] if sorted_langs else 'Unknown'
        
        return {
            'primary_language': primary_language,
            'language_count': len(languages),
            'language_distribution': dict(sorted_langs[:5]),  # Top 5 languages
            'is_polyglot': len([l for l in distribution.values() if l > 10]) >= 3
        }
    
    def assess_project_maturity(self, repo_data, repo_stats):
        """Assess the maturity level of a project"""
        score = 0
        factors = []
        
        # Stars indicate community interest
        stars = repo_data.get('stars', 0)
        if stars >= 100:
            score += 25
            factors.append('Popular (100+ stars)')
        elif stars >= 10:
            score += 15
            factors.append('Some interest (10+ stars)')
        elif stars >= 1:
            score += 5
            factors.append('Has stars')
        
        # Forks indicate reusability
        forks = repo_data.get('forks', 0)
        if forks >= 10:
            score += 20
            factors.append('Actively forked')
        elif forks >= 1:
            score += 10
            factors.append('Has forks')
        
        # Commit count indicates development effort
        commit_count = repo_stats.get('commit_count', 0)
        if commit_count >= 100:
            score += 25
            factors.append('Significant development')
        elif commit_count >= 20:
            score += 15
            factors.append('Active development')
        elif commit_count >= 5:
            score += 5
            factors.append('Some development')
        
        # Has description
        if repo_data.get('description'):
            score += 10
            factors.append('Has documentation')
        
        # Multiple contributors
        contributors = repo_stats.get('contributors', [])
        if len(contributors) > 2:
            score += 15
            factors.append('Team project')
        elif len(contributors) == 2:
            score += 10
            factors.append('Collaborative project')
        
        # Not a fork
        if not repo_data.get('fork', False):
            score += 5
            factors.append('Original work')
        
        # Determine maturity level
        if score >= 70:
            level = 'Production'
        elif score >= 50:
            level = 'Mature'
        elif score >= 30:
            level = 'Growing'
        elif score >= 15:
            level = 'Early Stage'
        else:
            level = 'Initial'
        
        return {
            'score': min(score, 100),
            'level': level,
            'factors': factors
        }
    
    def calculate_code_velocity(self, commits):
        """Calculate code velocity based on commit history"""
        if not commits:
            return {
                'commits_per_month': 0,
                'velocity_rating': 'Inactive',
                'trend': 'No data'
            }
        
        # Get date range
        dates = []
        for c in commits:
            try:
                date = datetime.fromisoformat(c.get('date', '').replace('Z', '+00:00'))
                dates.append(date.replace(tzinfo=None))
            except:
                pass
        
        if not dates:
            return {
                'commits_per_month': 0,
                'velocity_rating': 'Inactive',
                'trend': 'No data'
            }
        
        # Calculate commits per month
        date_range = max(dates) - min(dates)
        months = max(date_range.days / 30, 1)
        commits_per_month = len(commits) / months
        
        # Rating
        if commits_per_month >= 20:
            rating = 'Very Active'
        elif commits_per_month >= 10:
            rating = 'Active'
        elif commits_per_month >= 5:
            rating = 'Moderate'
        elif commits_per_month >= 1:
            rating = 'Low'
        else:
            rating = 'Inactive'
        
        # Trend (compare first half vs second half)
        mid_point = len(dates) // 2
        if mid_point > 0:
            recent_dates = dates[:mid_point]
            older_dates = dates[mid_point:]
            
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_count = sum(1 for d in recent_dates if d > thirty_days_ago)
            
            if recent_count > len(dates) * 0.3:
                trend = 'Increasing'
            elif recent_count < len(dates) * 0.1:
                trend = 'Decreasing'
            else:
                trend = 'Stable'
        else:
            trend = 'Insufficient data'
        
        return {
            'commits_per_month': round(commits_per_month, 1),
            'velocity_rating': rating,
            'trend': trend
        }
    
    def calculate_quality_score(self, analysis):
        """Calculate overall code quality score"""
        score = 0
        
        # Commit analysis (30 points)
        commit_analysis = analysis.get('commit_analysis', {})
        if commit_analysis.get('ownership_percentage', 0) >= 50:
            score += 15
        elif commit_analysis.get('ownership_percentage', 0) >= 25:
            score += 10
        
        if commit_analysis.get('commit_quality', 0) >= 50:
            score += 10
        elif commit_analysis.get('commit_quality', 0) >= 25:
            score += 5
        
        if commit_analysis.get('recent_activity'):
            score += 5
        
        # Project maturity (30 points)
        maturity = analysis.get('project_maturity', {})
        maturity_score = maturity.get('score', 0)
        score += int(maturity_score * 0.3)
        
        # Contributor analysis (20 points)
        contributor = analysis.get('contributor_analysis', {})
        if contributor.get('is_primary_contributor'):
            score += 15
        elif contributor.get('contribution_share', 0) >= 25:
            score += 10
        
        if contributor.get('collaboration_level') == 'Team':
            score += 5
        
        # Code velocity (20 points)
        velocity = analysis.get('code_velocity', {})
        velocity_rating = velocity.get('velocity_rating', '')
        if velocity_rating == 'Very Active':
            score += 15
        elif velocity_rating == 'Active':
            score += 12
        elif velocity_rating == 'Moderate':
            score += 8
        elif velocity_rating == 'Low':
            score += 4
        
        if velocity.get('trend') == 'Increasing':
            score += 5
        elif velocity.get('trend') == 'Stable':
            score += 3
        
        return min(score, 100)
    
    def analyze_all_repositories(self, repos_data, github_service, username):
        """Analyze all repositories and aggregate results"""
        all_analyses = []
        total_commits = 0
        total_user_commits = 0
        languages_aggregate = defaultdict(int)
        
        for repo in repos_data[:10]:  # Limit to top 10 repos for performance
            repo_name = repo.get('name')
            if not repo_name:
                continue
            
            # Fetch detailed stats
            repo_stats = github_service.fetch_repo_stats(username, repo_name)
            
            # Analyze
            analysis = self.analyze_repository(repo, repo_stats)
            analysis['repo_name'] = repo_name
            all_analyses.append(analysis)
            
            # Aggregate
            commit_analysis = analysis.get('commit_analysis', {})
            total_commits += commit_analysis.get('total_count', 0)
            total_user_commits += commit_analysis.get('user_commits', 0)
            
            for lang, pct in analysis.get('language_analysis', {}).get('language_distribution', {}).items():
                languages_aggregate[lang] += pct
        
        # Calculate aggregate metrics
        overall_ownership = (total_user_commits / total_commits * 100) if total_commits > 0 else 0
        avg_quality_score = sum(a.get('quality_score', 0) for a in all_analyses) / len(all_analyses) if all_analyses else 0
        
        # Normalize language distribution
        total_lang_score = sum(languages_aggregate.values())
        normalized_languages = {
            lang: round(score / total_lang_score * 100, 1) 
            for lang, score in languages_aggregate.items()
        } if total_lang_score > 0 else {}
        
        return {
            'repositories_analyzed': len(all_analyses),
            'total_commits': total_commits,
            'user_commits': total_user_commits,
            'overall_ownership': round(overall_ownership, 1),
            'average_quality_score': round(avg_quality_score, 1),
            'top_languages': dict(sorted(normalized_languages.items(), key=lambda x: x[1], reverse=True)[:5]),
            'individual_analyses': all_analyses
        }
