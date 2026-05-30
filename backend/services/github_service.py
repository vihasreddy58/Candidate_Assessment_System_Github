import os
import re
import base64
from datetime import datetime
import requests
from dotenv import load_dotenv

load_dotenv()


class GitHubService:
    def __init__(self):
        self.base_url = 'https://api.github.com'
        self.token = os.getenv('GITHUB_TOKEN')
        self.headers = {
            'Accept': 'application/vnd.github.v3+json'
        }
        if self.token:
            self.headers['Authorization'] = f'token {self.token}'

    def fetch_user_data(self, username_or_url):
        username = self.extract_username(username_or_url)
        print(f"Fetching GitHub data for: {username}")

        try:
            profile = self.fetch_profile(username)
            repositories = self.fetch_repositories(username)
            language_stats = self.aggregate_language_stats(repositories)
            contribution_stats = self.fetch_contribution_stats(username, repositories)

            return {
                'profile': profile,
                'repositories': repositories,
                'language_stats': language_stats,
                'contribution_stats': contribution_stats,
                'fetched_at': datetime.utcnow().isoformat()
            }
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise Exception(f"GitHub user '{username}' not found")
            elif e.response.status_code == 403:
                raise Exception('GitHub API rate limit exceeded. Please configure GITHUB_TOKEN in .env file')
            raise

    def extract_username(self, username_or_url):
        if '/' not in username_or_url and '.' not in username_or_url:
            return username_or_url

        match = re.search(r'github\.com/([a-zA-Z0-9-]+)', username_or_url)
        if match:
            return match.group(1)
        return username_or_url

    def fetch_profile(self, username):
        response = requests.get(f'{self.base_url}/users/{username}', headers=self.headers)
        response.raise_for_status()
        data = response.json()

        return {
            'login': data.get('login'),
            'name': data.get('name'),
            'bio': data.get('bio'),
            'company': data.get('company'),
            'location': data.get('location'),
            'email': data.get('email'),
            'blog': data.get('blog'),
            'avatar_url': data.get('avatar_url'),
            'followers': data.get('followers', 0),
            'following': data.get('following', 0),
            'public_repos': data.get('public_repos', 0),
            'public_gists': data.get('public_gists', 0),
            'created_at': data.get('created_at'),
            'updated_at': data.get('updated_at'),
            'account_age': self.calculate_account_age(data.get('created_at'))
        }

    def calculate_account_age(self, created_at):
        if not created_at:
            return 'Unknown'
        created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        now = datetime.now(created.tzinfo)
        diff = now - created
        years = diff.days // 365
        months = (diff.days % 365) // 30
        if years > 0:
            return f"{years} year{'s' if years > 1 else ''} {months} month{'s' if months != 1 else ''}"
        return f"{months} month{'s' if months != 1 else ''}"

    def fetch_repositories(self, username):
        all_repos = []
        page = 1
        per_page = 100

        while True:
            response = requests.get(
                f'{self.base_url}/users/{username}/repos',
                headers=self.headers,
                params={'per_page': per_page, 'page': page, 'sort': 'updated', 'direction': 'desc'}
            )
            response.raise_for_status()
            repos = response.json()

            if not repos:
                break

            all_repos.extend(repos)

            if len(repos) < per_page or len(all_repos) >= 100:
                break
            page += 1

        return [
            {
                'name': repo.get('name'),
                'full_name': repo.get('full_name'),
                'description': repo.get('description'),
                'language': repo.get('language'),
                'stars': repo.get('stargazers_count', 0),
                'forks': repo.get('forks_count', 0),
                'watchers': repo.get('watchers_count', 0),
                'size': repo.get('size', 0),
                'created_at': repo.get('created_at'),
                'updated_at': repo.get('updated_at'),
                'pushed_at': repo.get('pushed_at'),
                'is_private': repo.get('private', False),
                'is_fork': repo.get('fork', False),
                'default_branch': repo.get('default_branch'),
                'topics': repo.get('topics', []),
                'url': repo.get('html_url'),
                'clone_url': repo.get('clone_url'),
                'has_issues': repo.get('has_issues', False),
                'open_issues': repo.get('open_issues_count', 0),
                'license': repo.get('license', {}).get('name') if repo.get('license') else None
            }
            for repo in all_repos
        ]

    def fetch_repository_contents(self, username, repo_name, path=''):
        try:
            response = requests.get(
                f'{self.base_url}/repos/{username}/{repo_name}/contents/{path}',
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return []
            raise

    def fetch_file_content(self, username, repo_name, file_path):
        try:
            response = requests.get(
                f'{self.base_url}/repos/{username}/{repo_name}/contents/{file_path}',
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            content = data.get('content', '')
            return base64.b64decode(content).decode('utf-8')
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise
        except Exception:
            return None

    def fetch_languages(self, username, repo_name):
        try:
            response = requests.get(
                f'{self.base_url}/repos/{username}/{repo_name}/languages',
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            return {}

    def aggregate_language_stats(self, repositories):
        language_totals = {}
        total_bytes = 0

        for repo in repositories[:20]:  
            if repo.get('language'):
                lang = repo['language']
                size = repo.get('size', 0)
                language_totals[lang] = language_totals.get(lang, 0) + size
                total_bytes += size

        result = {}
        for lang, bytes_count in language_totals.items():
            percentage = (bytes_count / total_bytes * 100) if total_bytes > 0 else 0
            result[lang] = {
                'bytes': bytes_count,
                'percentage': round(percentage, 2)
            }

        return dict(sorted(result.items(), key=lambda x: x[1]['bytes'], reverse=True))

    def fetch_contribution_stats(self, username, repositories):
        total_commits = 0
        total_stars = sum(repo.get('stars', 0) for repo in repositories)
        total_forks = sum(repo.get('forks', 0) for repo in repositories)
        
        # Count active repositories (updated in last 6 months)
        from datetime import timedelta
        six_months_ago = datetime.utcnow() - timedelta(days=180)
        active_repos = 0
        
        for repo in repositories:
            updated = repo.get('updated_at')
            if updated:
                try:
                    updated_date = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                    if updated_date.replace(tzinfo=None) > six_months_ago:
                        active_repos += 1
                except:
                    pass

        return {
            'total_stars': total_stars,
            'total_forks': total_forks,
            'total_repositories': len(repositories),
            'active_repositories': active_repos,
            'contribution_activity': 'Active' if active_repos > 2 else 'Low'
        }

    def fetch_commits(self, username, repo_name, per_page=100):
        try:
            response = requests.get(
                f'{self.base_url}/repos/{username}/{repo_name}/commits',
                headers=self.headers,
                params={'per_page': per_page}
            )
            response.raise_for_status()
            commits = response.json()
            return [
                {
                    'sha': c.get('sha', '')[:7],
                    'message': c.get('commit', {}).get('message', ''),
                    'author': c.get('commit', {}).get('author', {}).get('name', ''),
                    'date': c.get('commit', {}).get('author', {}).get('date', ''),
                    'is_user': c.get('author', {}).get('login', '').lower() == username.lower() if c.get('author') else False
                }
                for c in commits
            ]
        except Exception as e:
            return []

    def fetch_repo_contributors(self, username, repo_name):
        """Fetch contributors for a repository"""
        try:
            response = requests.get(
                f'{self.base_url}/repos/{username}/{repo_name}/contributors',
                headers=self.headers,
                params={'per_page': 10}
            )
            response.raise_for_status()
            contributors = response.json()
            return [
                {
                    'login': c.get('login', ''),
                    'contributions': c.get('contributions', 0),
                    'is_owner': c.get('login', '').lower() == username.lower()
                }
                for c in contributors
            ]
        except Exception:
            return []

    def fetch_repo_stats(self, username, repo_name):
        """Fetch detailed repository statistics"""
        stats = {
            'commits': [],
            'contributors': [],
            'languages': {},
            'commit_count': 0,
            'user_commit_count': 0
        }
        
        # Fetch commits
        commits = self.fetch_commits(username, repo_name, per_page=100)
        stats['commits'] = commits
        stats['commit_count'] = len(commits)
        stats['user_commit_count'] = sum(1 for c in commits if c.get('is_user'))
        
        # Fetch contributors
        stats['contributors'] = self.fetch_repo_contributors(username, repo_name)
        
        # Fetch languages
        stats['languages'] = self.fetch_languages(username, repo_name)
        
        return stats
