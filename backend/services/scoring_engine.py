from datetime import datetime, timezone


## scoring engine is updated after all features are implemented.
class ScoringEngine:
    def __init__(self):
        # Weights sum to 1.0
        self.weights = {
            'skill_authenticity': 0.60,
            'code_quality': 0.10,
            'commit_activity': 0.10,
            'tech_stack': 0.10,
            'profile_signal': 0.10
        }

    def calculate_scores(self, github_data, tech_stack_data, matching_results, code_quality=None, contributions=None):
        """Compute overall score with weighted components."""
        print("Calculating scores with multi-factor model...")

        stats = matching_results.get('statistics', {})
        skill_matching_skipped = bool(stats.get('skipped'))
        # UI expectation: skill authenticity should not be lower than the match percentage.
        # SkillMatcher's authenticity_score can differ slightly due to rounding; clamp via max().
        if skill_matching_skipped:
            skill_authenticity = 0.0
        else:
            skill_authenticity = max(
                float(stats.get('authenticity_score', 0) or 0),
                float(stats.get('match_percentage', 0) or 0),
            )

        code_quality_score = self._score_code_quality(code_quality)
        commit_score = self._score_commit_activity(contributions)
        stack_score = self._score_tech_stack(tech_stack_data)
        profile_score = self._score_profile(github_data)

        component_scores = {
            'skill_authenticity': skill_authenticity,
            'code_quality': code_quality_score,
            'commit_activity': commit_score,
            'tech_stack': stack_score,
            'profile_signal': profile_score,
        }

        active_components = [
            'code_quality',
            'commit_activity',
            'tech_stack',
            'profile_signal',
        ] if skill_matching_skipped else list(component_scores.keys())

        total_weight = sum(self.weights[name] for name in active_components)
        weighted_sum = sum(component_scores[name] * self.weights[name] for name in active_components)
        overall = (weighted_sum / total_weight) if total_weight > 0 else 0

        return {
            'overall': round(overall, 2),
            'breakdown': {
                'skill_authenticity': round(skill_authenticity, 2),
                'code_quality': round(code_quality_score, 2),
                'commit_activity': round(commit_score, 2),
                'tech_stack': round(stack_score, 2),
                'profile_signal': round(profile_score, 2)
            },
            'meta': {
                'skill_matching_skipped': skill_matching_skipped,
                'active_components': active_components,
            },
            'rating': self._get_rating(overall)
        }

    def _score_code_quality(self, code_quality):
        if not code_quality:
            return 0
        # Prefer numeric overall_score; fallback to grade mapping
        if 'overall_score' in code_quality:
            return max(0, min(100, code_quality.get('overall_score', 0)))
        grade = code_quality.get('grade')
        grade_map = {'A': 95, 'B': 80, 'C': 65, 'D': 45, 'F': 25}
        return grade_map.get(grade, 0)

    def _score_commit_activity(self, contributions):
        if not contributions:
            return 0
        summary = contributions.get('summary', {})
        total_commits = summary.get('total_commits', 0)
        recent = contributions.get('commit_activity', {}).get('total_recent_commits', 0)
        # Scale: reward recency more than absolute total
        recent_score = min(100, recent * 4)  # 25 recent commits => 100
        volume_score = min(100, total_commits / 200 * 100)
        return round((recent_score * 0.6) + (volume_score * 0.4), 2)

    def _score_tech_stack(self, tech_stack_data):
        if not tech_stack_data:
            return 0
        detected = tech_stack_data.get('detected_skills', {})
        if not detected:
            return 0
        breadth = min(len(detected), 25) / 25 * 100
        confidences = [v.get('confidence', 0) for v in detected.values() if v.get('confidence') is not None]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0
        return round((breadth * 0.6) + (avg_conf * 0.4), 2)

    def _score_profile(self, github_data):
        if not github_data:
            return 0

        profile = github_data.get('profile', {})
        contrib_stats = github_data.get('contribution_stats', {})

        public_repos = profile.get('public_repos', 0) or 0
        total_repos = contrib_stats.get('total_repositories', 0) or 0
        active_repos = contrib_stats.get('active_repositories', 0) or 0

        # Useful profile/portfolio indicators (avoid social popularity signals like followers).
        completeness_signals = [
            bool(profile.get('bio')),
            bool(profile.get('name')),
            bool(profile.get('location')),
            bool(profile.get('company')),
            bool(profile.get('blog'))
        ]
        completeness_score = (sum(1 for s in completeness_signals if s) / len(completeness_signals)) * 100

        # Portfolio depth: number of public repos (saturates at 25 repos).
        depth_score = min(100, (public_repos / 25) * 100)

        # Activity volume: currently active repos (saturates at 8 repos).
        active_volume_score = min(100, (active_repos / 8) * 100)

        # Activity consistency: percent of repos that are currently active.
        base_repos = total_repos or public_repos
        activity_consistency_score = min(100, (active_repos / base_repos) * 100) if base_repos > 0 else 0

        # Account maturity: rewards sustained presence without dominating the score.
        account_maturity_score = self._score_account_maturity(profile.get('created_at'))

        profile_score = (
            (completeness_score * 0.20) +
            (depth_score * 0.25) +
            (active_volume_score * 0.30) +
            (activity_consistency_score * 0.15) +
            (account_maturity_score * 0.10)
        )

        return round(min(100, max(0, profile_score)), 2)

    def _score_account_maturity(self, created_at):
        if not created_at:
            return 0
        try:
            created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            now = datetime.now(created_date.tzinfo or timezone.utc)
            age_days = max((now - created_date).days, 0)
            # 4+ years saturates maturity score.
            return min(100, (age_days / 1460) * 100)
        except Exception:
            return 0

    def _get_rating(self, score):
        if score >= 85:
            return 'Excellent'
        if score >= 70:
            return 'Very Good'
        if score >= 55:
            return 'Good'
        if score >= 40:
            return 'Average'
        return 'Below Average'
