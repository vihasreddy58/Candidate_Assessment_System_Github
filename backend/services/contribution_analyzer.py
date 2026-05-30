"""
Contribution Analyzer
Analyzes commits and contributions across GitHub repositories
"""
from datetime import datetime, timedelta
from collections import defaultdict


class ContributionAnalyzer:
    """Analyzes user's commit patterns and contributions"""
    
    def __init__(self, github_service):
        self.github_service = github_service

    def analyze_contributions(self, repositories, username):
        """
        Analyze commits and contributions across all repositories
        Returns detailed contribution metrics
        """
        print(f"Analyzing contributions for {username}...")
        
        # Separate owned vs forked repositories
        owned_repos = [r for r in repositories if not r.get('is_fork', False)]
        forked_repos = [r for r in repositories if r.get('is_fork', False)]
        
        # Analyze commits in owned repositories
        owned_analysis = self._analyze_owned_repos(owned_repos, username)
        
        # Analyze contributions to forked repositories (contributions to others)
        fork_analysis = self._analyze_forked_repos(forked_repos, username)
        
        # Calculate overall statistics
        total_commits = owned_analysis['total_commits'] + fork_analysis['total_commits']
        
        # Get commit activity over time
        commit_activity = self._analyze_commit_activity(owned_repos[:10], username)
        
        return {
            'summary': {
                'total_commits': total_commits,
                'owned_repo_commits': owned_analysis['total_commits'],
                'fork_contributions': fork_analysis['total_commits'],
                'repos_with_commits': owned_analysis['repos_with_commits'],
                'active_contributor': total_commits >= 50
            },
            'owned_repositories': owned_analysis,
            'contributions_to_others': fork_analysis,
            'commit_activity': commit_activity,
            'top_repositories': self._get_top_repos_by_commits(owned_analysis['repo_details']),
            'contribution_streak': self._calculate_streak(commit_activity)
        }

    def _analyze_owned_repos(self, repos, username):
        """Analyze commits in user's own repositories"""
        repo_details = []
        total_commits = 0
        repos_with_commits = 0
        
        # Analyze top 15 repos by stars/recency
        repos_to_analyze = sorted(
            repos,
            key=lambda x: (x.get('stars', 0), x.get('pushed_at', '')),
            reverse=True
        )[:15]
        
        for repo in repos_to_analyze:
            repo_name = repo['name']
            
            try:
                commits = self.github_service.fetch_commits(username, repo_name, per_page=100)
                
                # Count user's commits
                user_commits = [c for c in commits if c.get('is_user', False)]
                user_commit_count = len(user_commits)
                total_commit_count = len(commits)
                
                if user_commit_count > 0:
                    repos_with_commits += 1
                    total_commits += user_commit_count
                    
                    # Get recent commit dates
                    recent_commits = self._get_recent_commit_dates(user_commits[:10])
                    
                    # Analyze commit messages
                    message_quality = self._analyze_commit_messages(user_commits[:20])
                    
                    repo_details.append({
                        'name': repo_name,
                        'url': repo.get('url', ''),
                        'language': repo.get('language', 'Unknown'),
                        'stars': repo.get('stars', 0),
                        'user_commits': user_commit_count,
                        'total_commits': total_commit_count,
                        'ownership_percentage': round((user_commit_count / total_commit_count * 100) if total_commit_count > 0 else 0, 1),
                        'last_commit': recent_commits[0] if recent_commits else None,
                        'commit_message_quality': message_quality,
                        'is_active': self._is_recently_active(repo)
                    })
            except Exception as e:
                print(f"    Error analyzing {repo_name}: {str(e)}")
                continue
        
        # Sort by user commits
        repo_details.sort(key=lambda x: x['user_commits'], reverse=True)
        
        return {
            'total_commits': total_commits,
            'repos_analyzed': len(repos_to_analyze),
            'repos_with_commits': repos_with_commits,
            'repo_details': repo_details
        }

    def _analyze_forked_repos(self, forked_repos, username):
        """Analyze contributions to forked repositories (open source contributions)"""
        contributions = []
        total_commits = 0
        
        # Check top 10 forked repos for contributions
        for repo in forked_repos[:10]:
            repo_name = repo['name']
            
            try:
                commits = self.github_service.fetch_commits(username, repo_name, per_page=50)
                user_commits = [c for c in commits if c.get('is_user', False)]
                
                if user_commits:
                    total_commits += len(user_commits)
                    contributions.append({
                        'name': repo_name,
                        'url': repo.get('url', ''),
                        'original_repo': repo.get('full_name', repo_name),
                        'language': repo.get('language', 'Unknown'),
                        'commits': len(user_commits),
                        'last_contribution': user_commits[0].get('date') if user_commits else None,
                        'contribution_type': 'fork'
                    })
            except Exception as e:
                continue
        
        # Sort by commits
        contributions.sort(key=lambda x: x['commits'], reverse=True)
        
        return {
            'total_commits': total_commits,
            'repos_contributed': len(contributions),
            'contributions': contributions,
            'is_open_source_contributor': len(contributions) > 0
        }

    def _analyze_commit_activity(self, repos, username):
        """Analyze commit activity over time"""
        activity_by_month = defaultdict(int)
        activity_by_day = defaultdict(int)
        
        for repo in repos:
            try:
                commits = self.github_service.fetch_commits(username, repo['name'], per_page=50)
                user_commits = [c for c in commits if c.get('is_user', False)]
                
                for commit in user_commits:
                    date_str = commit.get('date', '')
                    if date_str:
                        try:
                            commit_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            month_key = commit_date.strftime('%Y-%m')
                            day_key = commit_date.strftime('%A')
                            activity_by_month[month_key] += 1
                            activity_by_day[day_key] += 1
                        except:
                            pass
            except:
                continue
        
        # Get last 6 months of activity
        recent_months = sorted(activity_by_month.items(), reverse=True)[:6]
        
        return {
            'monthly_activity': dict(reversed(recent_months)),
            'daily_distribution': dict(activity_by_day),
            'most_active_day': max(activity_by_day.items(), key=lambda x: x[1])[0] if activity_by_day else 'Unknown',
            'total_recent_commits': sum(dict(recent_months).values())
        }

    def _get_recent_commit_dates(self, commits):
        """Extract recent commit dates"""
        dates = []
        for commit in commits:
            date_str = commit.get('date', '')
            if date_str:
                try:
                    dates.append(date_str)
                except:
                    pass
        return dates

    def _analyze_commit_messages(self, commits):
        """Analyze quality of commit messages"""
        if not commits:
            return 'none'
        
        good_messages = 0
        for commit in commits:
            message = commit.get('message', '')
            first_line = message.split('\n')[0] if message else ''
            
            # Good message criteria
            good_length = 10 <= len(first_line) <= 72
            starts_properly = first_line and (first_line[0].isupper() or ':' in first_line[:20])
            
            if good_length and starts_properly:
                good_messages += 1
        
        ratio = good_messages / len(commits)
        if ratio >= 0.7:
            return 'excellent'
        elif ratio >= 0.5:
            return 'good'
        elif ratio >= 0.3:
            return 'average'
        return 'needs_improvement'

    def _is_recently_active(self, repo):
        """Check if repo has recent activity"""
        pushed_at = repo.get('pushed_at')
        if not pushed_at:
            return False
        
        try:
            pushed_date = datetime.fromisoformat(pushed_at.replace('Z', '+00:00'))
            ninety_days_ago = datetime.now(pushed_date.tzinfo) - timedelta(days=90)
            return pushed_date > ninety_days_ago
        except:
            return False

    def _get_top_repos_by_commits(self, repo_details):
        """Get top repositories by commit count"""
        return repo_details[:5]

    def _calculate_streak(self, commit_activity):
        """Calculate contribution streak information"""
        monthly = commit_activity.get('monthly_activity', {})
        
        if not monthly:
            return {
                'current_streak_months': 0,
                'longest_streak_months': 0,
                'is_consistent': False
            }
        
        # Check for consecutive months
        months = sorted(monthly.keys(), reverse=True)
        current_streak = 0
        
        for i, month in enumerate(months):
            if monthly.get(month, 0) > 0:
                current_streak += 1
            else:
                break
        
        return {
            'current_streak_months': current_streak,
            'active_months': len([m for m in monthly.values() if m > 0]),
            'is_consistent': current_streak >= 3
        }
