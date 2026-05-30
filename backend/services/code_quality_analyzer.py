
import os
import re
import ast
from datetime import datetime, timezone
from statistics import mean, pstdev

try:
    from dateutil import parser as date_parser
except Exception:  # pragma: no cover - optional dependency fallback
    date_parser = None

try:
    import textstat  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - optional dependency fallback
    textstat = None

try:
    from rapidfuzz import fuzz  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - optional dependency fallback
    fuzz = None

try:
    from radon.complexity import cc_visit  # type: ignore[import-not-found]
    from radon.metrics import mi_visit  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - optional dependency fallback
    cc_visit = None
    mi_visit = None

try:
    import esprima  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - optional dependency fallback
    esprima = None

try:
    import javalang  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - optional dependency fallback
    javalang = None


class RepositoryQualityAnalyzer:
    """Analyzes code quality indicators from GitHub repositories"""

    def __init__(self, github_service, enable_code_health=True, code_health_max_files=50, code_health_max_depth=6):
        self.github_service = github_service

        if enable_code_health is None:
            enable_code_health = os.getenv('ENABLE_CODE_HEALTH', 'false')
        self.enable_code_health = str(enable_code_health).strip().lower() in {'1', 'true', 'yes', 'y', 'on'}
        self.code_health_max_files = int(code_health_max_files or 0) if str(code_health_max_files).isdigit() else 30
        self.code_health_max_depth = int(code_health_max_depth or 0) if str(code_health_max_depth).isdigit() else 4
        
        # File patterns for quality indicators
        self.readme_patterns = ['README.md', 'README.txt', 'README.rst', 'readme.md']
        # NOTE: Excluded from scoring/evidence per request.
        # self.license_patterns = ['LICENSE', 'LICENSE.md', 'LICENSE.txt', 'license']
        self.license_patterns = []
        # self.test_patterns = ['test', 'tests', 'spec', 'specs', '__tests__', 'test_', '_test.py', '.test.js', '.spec.ts']
        self.test_patterns = []
        # self.ci_patterns = ['.github/workflows', '.travis.yml', '.circleci', 'Jenkinsfile', 'azure-pipelines.yml', '.gitlab-ci.yml']
        self.ci_patterns = []
        self.doc_patterns = ['docs', 'documentation', 'doc', 'wiki']
        self.config_patterns = ['.gitignore', '.editorconfig', '.eslintrc', '.prettierrc', 'pyproject.toml', 'setup.py', 'setup.cfg']
        self.dependency_patterns = [
            'package.json', 'requirements.txt', 'pyproject.toml', 'pipfile',
            'pom.xml', 'build.gradle', 'composer.json', 'go.mod', 'cargo.toml'
        ]
        self.env_patterns = ['.env.example', '.env.sample', '.env.template', 'sample.env']
        self.example_patterns = ['examples', 'example', 'demo', 'sample', 'samples']
        self.changelog_patterns = ['changelog.md', 'history.md', 'release-notes.md']
        self.architecture_patterns = ['architecture.md', 'design.md', 'system-design.md']
        
        # Default grade thresholds, later adapted dynamically per candidate portfolio.
        self.grade_thresholds = {
            'A': 85,
            'B': 70,
            'C': 55,
            'D': 40,
            'F': 0
        }

        # self.category_weights = {
        #     'documentation': 0.22,
        #     'testing': 0.20,
        #     'code_organization': 0.16,
        #     'maintainability': 0.16,
        #     'commit_quality': 0.12,
        #     # Optional: real code analysis (Python-focused via radon).
        #     'code_health': 0.14
        # }
        self.category_weights = {
            'documentation': 0.15,
            'code_organization': 0.30,
            'commit_quality': 0.25,
            'code_health': 0.30
        }

    def analyze_code_quality(self, repositories, username):
        print(f"Analyzing code quality for {len(repositories)} repositories...")
        
        # Select top repositories to analyze (by stars + recency)
        repos_to_analyze = self._select_repos_for_analysis(repositories)

        if not repos_to_analyze:
            return {
                'overall_score': 0,
                'grade': 'F',
                'grade_label': self._get_grade_label('F'),
                'repositories_analyzed': 0,
                'metrics': {},
                'detailed_analysis': [],
                'suggestions': [
                    {
                        'category': 'Repository Selection',
                        'priority': 'high',
                        'suggestion': 'No non-fork repositories were found for analysis.',
                        'impact': 'Cannot evaluate practical code quality without project history'
                    }
                ],
                'strengths': [],
                'weaknesses': []
            }
        
        repo_quality_scores = []
        detailed_analysis = []
        
        for repo in repos_to_analyze:
            repo_analysis = self._analyze_repository_quality(repo, username)
            repo_quality_scores.append(repo_analysis['score'])
            detailed_analysis.append(repo_analysis)

        # Calibrate repo scores against candidate portfolio to reduce strict, static behavior.
        self._apply_dynamic_calibration(detailed_analysis)
        calibrated_scores = [r.get('score', 0) for r in detailed_analysis]
        dynamic_thresholds = self._derive_dynamic_thresholds(calibrated_scores)
        
        # Calculate overall score (weighted by repo importance)
        overall_score = self._calculate_weighted_score(calibrated_scores, repos_to_analyze)
        grade = self._score_to_grade(overall_score, dynamic_thresholds=dynamic_thresholds)
        
        # Aggregate metrics
        metrics = self._aggregate_metrics(detailed_analysis)
        
        # Generate improvement suggestions
        suggestions = self._generate_suggestions(metrics, detailed_analysis)
        
        return {
            'overall_score': round(self._clamp(overall_score, 0, 100), 1),
            'grade': grade,
            'grade_label': self._get_grade_label(grade),
            'repositories_analyzed': len(repos_to_analyze),
            'metrics': metrics,
            'detailed_analysis': detailed_analysis,
            'suggestions': suggestions,
            'strengths': self._identify_strengths(metrics),
            'weaknesses': self._identify_weaknesses(metrics),
            'scoring_model': {
                'type': 'hybrid-dynamic',
                'uses_textstat': bool(textstat),
                'uses_dateutil': bool(date_parser),
                'uses_rapidfuzz': bool(fuzz),
                'uses_radon': bool(cc_visit and mi_visit),
                'code_health_enabled': bool(self.enable_code_health),
                'dynamic_grade_thresholds': dynamic_thresholds
            }
        }

    def _select_repos_for_analysis(self, repositories, max_repos=10):
        """Select most relevant repositories for analysis"""
        # Filter out forks
        original_repos = [r for r in repositories if not r.get('is_fork', False)]
        
        # Sort by stars and recency for more representative quality sampling.
        sorted_repos = sorted(
            original_repos,
            key=lambda x: (
                x.get('stars', 0),
                self._to_timestamp(x.get('pushed_at') or x.get('updated_at'))
            ),
            reverse=True
        )
        
        return sorted_repos[:max_repos]

    def _analyze_repository_quality(self, repo, username):
        """Analyze quality indicators for a single repository"""
        repo_name = repo['name']
        print(f"  Analyzing quality: {repo_name}")
        
        scores = {
            'documentation': 0,
            # 'testing': 0,
            'code_organization': 0,
            # 'maintainability': 0,
            'commit_quality': 0
        }
        
        evidence = {
            'has_readme': False,
            'readme_quality': 'none',
            'readme_quality_score': 0,
            'readme_readability': None,
            'readme_has_installation': False,
            'readme_has_usage': False,
            'readme_has_features': False,
            # NOTE: excluded from this analyzer per request.
            'has_license': False,
            'has_tests': False,
            'test_coverage_indicator': 'none',
            'has_ci_cd': False,
            'has_documentation': False,
            'has_contributing': False,
            'has_examples': False,
            'has_architecture_doc': False,
            'code_structure': 'basic',
            'commit_frequency': 'low',
            'commit_frequency_score': 0,
            'commit_message_quality': 'average',
            'commit_message_score': 0,
            'directory_count': 0,
            'file_count': 0,
            'code_health_enabled': bool(self.enable_code_health),
            'code_health_available': False,
            'code_health_files_analyzed': 0,
            'code_health_language': None,
            'code_health_languages': [],
            'code_health_avg_mi': None,
            'code_health_avg_cc': None
        }
        
        try:
            # Fetch repository contents
            contents = self.github_service.fetch_repository_contents(username, repo_name)
            
            if contents:
                evidence = self._analyze_repo_contents(contents, evidence, repo, username, repo_name)
                scores = self._calculate_category_scores(evidence, repo)

                # Optional "actual code" quality analysis (gated for runtime cost).
                if self.enable_code_health:
                    code_health = self._analyze_code_health(username, repo_name)
                    if code_health and code_health.get('score') is not None:
                        scores['code_health'] = round(self._clamp(code_health['score'], 0, 100), 1)
                        evidence['code_health_available'] = True
                        evidence['code_health_files_analyzed'] = int(code_health.get('files_analyzed', 0) or 0)
                        evidence['code_health_language'] = code_health.get('language')
                        evidence['code_health_languages'] = list(code_health.get('languages') or [])
                        evidence['code_health_avg_mi'] = code_health.get('avg_mi')
                        evidence['code_health_avg_cc'] = code_health.get('avg_cc')
            
        except Exception as e:
            print(f"    Error analyzing {repo_name}: {str(e)}")
        
        # Weighted total score for this repository.
        # IMPORTANT: normalize weights over only included categories.
        total_score = self._weighted_category_score(scores)
        
        return {
            'name': repo_name,
            'score': round(total_score, 1),
            'score_raw': round(total_score, 1),
            'grade': self._score_to_grade(total_score),
            'scores': scores,
            'evidence': evidence,
            'language': repo.get('language', 'Unknown'),
            'stars': repo.get('stars', 0),
            'url': repo.get('url', '')
        }

    def _weighted_category_score(self, scores):
        """Weighted average across categories present in `scores`.

        This keeps the overall score stable when optional categories are disabled
        (or unavailable) by re-normalizing the remaining weights.
        """
        if not scores:
            return 0

        active = []
        for key, score in scores.items():
            weight = float(self.category_weights.get(key, 0) or 0)
            if weight > 0:
                active.append((float(score or 0), weight))

        if not active:
            return 0

        total_weight = sum(w for _, w in active)
        weighted_sum = sum(s * w for s, w in active)
        return self._clamp(weighted_sum / max(total_weight, 1e-9), 0, 100)

    def _analyze_code_health(self, username, repo_name):
        """Compute a Code Health score from actual source files.

        Supported today (best-effort, dependency-optional):
        - Python: Radon MI + CC if available, otherwise AST-based CC estimate.
        - JavaScript/TypeScript: AST-based CC estimate via `esprima` if available.
        - Java: AST-based CC estimate via `javalang` if available.

        Returns None when analysis can't be performed (no eligible files).
        """
        candidates = [
            ('Python', {'.py'}),
            ('TypeScript', {'.ts', '.tsx'}),
            ('JavaScript', {'.js', '.jsx'}),
            ('Java', {'.java'}),
        ]

        results = []
        for language, exts in candidates:
            file_paths = self._collect_repo_file_paths(
                username,
                repo_name,
                exts=exts,
                max_files=self.code_health_max_files,
                max_depth=self.code_health_max_depth,
            )
            if not file_paths:
                continue

            contents = []
            for path in file_paths:
                content = self.github_service.fetch_file_content(username, repo_name, path)
                if not content or len(content) > 120_000:
                    continue
                contents.append(content)

            if not contents:
                continue

            analysis = None
            if language == 'Python':
                analysis = self._analyze_python_code_health(contents)
            elif language in {'JavaScript', 'TypeScript'}:
                analysis = self._analyze_js_ts_code_health(contents, language=language)
            elif language == 'Java':
                analysis = self._analyze_java_code_health(contents)

            if analysis and analysis.get('score') is not None:
                analysis['language'] = language
                results.append(analysis)

        if not results:
            return None

        # Combine multi-language results rather than picking a single winner.
        #
        # Rationale:
        # - Repos are often polyglot; picking one language can hide complexity elsewhere.
        # - A naive average can swing too hard when one language has only a few files.
        #
        # We compute a capped, file-count-weighted average:
        #   weight_i = clamp(files_i, 1, 20)
        #   score    = sum(score_i * weight_i) / sum(weight_i)
        # This makes coverage matter, but prevents any single language from completely
        # dominating the combined score.

        def _weight(files_analyzed: int) -> float:
            try:
                n = int(files_analyzed or 0)
            except Exception:
                n = 0
            return float(self._clamp(max(n, 1), 1, 20))

        total_files = 0
        weighted_score_sum = 0.0
        weight_sum = 0.0
        weighted_cc_sum = 0.0
        cc_weight_sum = 0.0

        weighted_mi_sum = 0.0
        mi_weight_sum = 0.0

        languages = []
        for r in results:
            files = int(r.get('files_analyzed', 0) or 0)
            score = float(r.get('score', 0) or 0)
            w = _weight(files)

            languages.append(r.get('language'))
            total_files += max(files, 0)
            weighted_score_sum += score * w
            weight_sum += w

            avg_cc = r.get('avg_cc')
            if avg_cc is not None:
                try:
                    weighted_cc_sum += float(avg_cc) * w
                    cc_weight_sum += w
                except Exception:
                    pass

            avg_mi = r.get('avg_mi')
            if avg_mi is not None:
                try:
                    weighted_mi_sum += float(avg_mi) * w
                    mi_weight_sum += w
                except Exception:
                    pass

        combined_score = weighted_score_sum / max(weight_sum, 1e-9)
        combined_avg_cc = (weighted_cc_sum / max(cc_weight_sum, 1e-9)) if cc_weight_sum else None
        combined_avg_mi = (weighted_mi_sum / max(mi_weight_sum, 1e-9)) if mi_weight_sum else None

        unique_langs = [l for l in dict.fromkeys(languages) if l]  # stable, unique
        combined_language = unique_langs[0] if len(unique_langs) == 1 else 'Mixed'

        return {
            'score': float(self._clamp(combined_score, 0, 100)),
            'files_analyzed': int(total_files),
            'avg_mi': round(float(combined_avg_mi), 2) if combined_avg_mi is not None else None,
            'avg_cc': round(float(combined_avg_cc), 2) if combined_avg_cc is not None else None,
            'language': combined_language,
            'languages': unique_langs,
        }

    def _analyze_python_code_health(self, contents):
        """Python code health: prefer Radon MI+CC; fallback to AST CC + size heuristic."""
        if cc_visit and mi_visit:
            mi_values = []
            avg_cc_values = []

            for content in contents:
                try:
                    mi = float(mi_visit(content, multi=True))
                    blocks = cc_visit(content)
                    complexities = [float(b.complexity) for b in blocks] if blocks else []
                    avg_cc = mean(complexities) if complexities else 0.0
                    mi_values.append(mi)
                    avg_cc_values.append(avg_cc)
                except Exception:
                    continue

            if not mi_values:
                return None

            avg_mi = mean(mi_values)
            avg_cc = mean(avg_cc_values) if avg_cc_values else 0.0
            base = self._clamp(avg_mi, 0, 100)
            cc_penalty = self._clamp(max(avg_cc - 6.0, 0.0) * 4.5, 0, 28)
            score = self._clamp(base - cc_penalty, 0, 100)

            return {
                'score': float(score),
                'files_analyzed': len(mi_values),
                'avg_mi': round(float(avg_mi), 2),
                'avg_cc': round(float(avg_cc), 2),
            }

        # Fallback: AST-based cyclomatic estimate + size penalty.
        complexities = []
        locs = []
        for content in contents:
            try:
                tree = ast.parse(content)
            except Exception:
                continue

            loc = max(len(content.splitlines()), 1)
            locs.append(loc)
            complexities.append(float(self._estimate_python_cc(tree)))

        if not complexities:
            return None

        avg_cc = mean(complexities)
        avg_loc = mean(locs) if locs else 0.0
        # Map to 0-100: start from 100, penalize complexity and very large files.
        cc_penalty = self._clamp(max(avg_cc - 6.0, 0.0) * 8.0, 0, 65)
        size_penalty = self._clamp(max(avg_loc - 350.0, 0.0) / 50.0 * 2.0, 0, 20)
        score = self._clamp(100.0 - cc_penalty - size_penalty, 0, 100)

        return {
            'score': float(score),
            'files_analyzed': len(complexities),
            'avg_mi': None,
            'avg_cc': round(float(avg_cc), 2),
        }

    def _estimate_python_cc(self, tree):
        """Very small cyclomatic-complexity estimator for Python AST."""
        decision_nodes = (
            ast.If,
            ast.For,
            ast.AsyncFor,
            ast.While,
            ast.Try,
            ast.With,
            ast.AsyncWith,
            ast.ExceptHandler,
            ast.Match,
        )

        count = 1
        for node in ast.walk(tree):
            if isinstance(node, decision_nodes):
                count += 1
            elif isinstance(node, ast.BoolOp):
                # Each extra boolean operand increases paths.
                count += max(len(getattr(node, 'values', []) or []) - 1, 0)
        return count

    def _analyze_js_ts_code_health(self, contents, language):
        """JS/TS code health using esprima AST (complexity + size heuristic)."""
        if not esprima:
            return None

        complexities = []
        locs = []
        for content in contents:
            try:
                # tolerant parsing to survive partial files.
                tree = esprima.parseModule(content, tolerant=True, jsx=True)
            except Exception:
                try:
                    tree = esprima.parseScript(content, tolerant=True, jsx=True)
                except Exception:
                    continue

            loc = max(len(content.splitlines()), 1)
            locs.append(loc)
            complexities.append(float(self._estimate_esprima_cc(tree)))

        if not complexities:
            return None

        avg_cc = mean(complexities)
        avg_loc = mean(locs) if locs else 0.0
        cc_penalty = self._clamp(max(avg_cc - 6.0, 0.0) * 8.0, 0, 65)
        size_penalty = self._clamp(max(avg_loc - 450.0, 0.0) / 60.0 * 2.0, 0, 20)
        score = self._clamp(100.0 - cc_penalty - size_penalty, 0, 100)

        return {
            'score': float(score),
            'files_analyzed': len(complexities),
            'avg_mi': None,
            'avg_cc': round(float(avg_cc), 2),
        }

    def _estimate_esprima_cc(self, node):
        """Cyclomatic estimate for esprima AST (counts decision points)."""
        count = 1
        stack = [node]
        while stack:
            current = stack.pop()
            if current is None:
                continue

            node_type = getattr(current, 'type', None)
            if node_type in {
                'IfStatement',
                'ForStatement',
                'ForInStatement',
                'ForOfStatement',
                'WhileStatement',
                'DoWhileStatement',
                'CatchClause',
                'ConditionalExpression',
            }:
                count += 1
            elif node_type == 'LogicalExpression':
                op = getattr(current, 'operator', None)
                if op in {'&&', '||'}:
                    count += 1
            elif node_type == 'SwitchCase':
                # Only count explicit cases (not default).
                if getattr(current, 'test', None) is not None:
                    count += 1

            # Walk children: esprima nodes are objects with __dict__.
            if hasattr(current, '__dict__'):
                for value in current.__dict__.values():
                    if isinstance(value, list):
                        stack.extend(value)
                    else:
                        stack.append(value)
        return count

    def _analyze_java_code_health(self, contents):
        """Java code health using javalang AST (complexity + size heuristic)."""
        if not javalang:
            return None

        complexities = []
        locs = []
        for content in contents:
            try:
                tree = javalang.parse.parse(content)
            except Exception:
                continue

            loc = max(len(content.splitlines()), 1)
            locs.append(loc)
            complexities.append(float(self._estimate_javalang_cc(tree)))

        if not complexities:
            return None

        avg_cc = mean(complexities)
        avg_loc = mean(locs) if locs else 0.0
        cc_penalty = self._clamp(max(avg_cc - 8.0, 0.0) * 7.0, 0, 70)
        size_penalty = self._clamp(max(avg_loc - 550.0, 0.0) / 80.0 * 2.0, 0, 20)
        score = self._clamp(100.0 - cc_penalty - size_penalty, 0, 100)

        return {
            'score': float(score),
            'files_analyzed': len(complexities),
            'avg_mi': None,
            'avg_cc': round(float(avg_cc), 2),
        }

    def _estimate_javalang_cc(self, tree):
        """Cyclomatic estimate for javalang AST."""
        decision_types = (
            getattr(javalang.tree, 'IfStatement', object),
            getattr(javalang.tree, 'ForStatement', object),
            getattr(javalang.tree, 'WhileStatement', object),
            getattr(javalang.tree, 'DoStatement', object),
            getattr(javalang.tree, 'CatchClause', object),
            getattr(javalang.tree, 'SwitchStatementCase', object),
            getattr(javalang.tree, 'TernaryExpression', object),
        )
        boolop_type = getattr(javalang.tree, 'BinaryOperation', object)

        count = 1
        for _, node in tree.filter(javalang.tree.Node):
            if isinstance(node, decision_types):
                # SwitchStatementCase includes default; count only if it has a case.
                if node.__class__.__name__ == 'SwitchStatementCase':
                    if getattr(node, 'case', None) is not None:
                        count += 1
                else:
                    count += 1
            elif isinstance(node, boolop_type):
                op = getattr(node, 'operator', None)
                if op in {'&&', '||'}:
                    count += 1
        return count

    def _collect_repo_file_paths(self, username, repo_name, exts, max_files, max_depth):
        """Collect file paths in the repo via GitHub contents API (depth-limited)."""
        max_files = max(0, int(max_files or 0))
        max_depth = max(0, int(max_depth or 0))
        if max_files <= 0:
            return []

        ignored_dirs = {
            '.git', '.github', '__pycache__', 'node_modules', 'dist', 'build',
            '.venv', 'venv', 'env', '.env', '.tox', '.pytest_cache',
        }

        results = []
        queue = [('', 0)]
        seen_dirs = set()

        while queue and len(results) < max_files:
            path, depth = queue.pop(0)
            if (path, depth) in seen_dirs:
                continue
            seen_dirs.add((path, depth))

            if depth > max_depth:
                continue

            items = self.github_service.fetch_repository_contents(username, repo_name, path)
            if not items:
                continue

            for item in items:
                item_type = item.get('type')
                name = (item.get('name') or '').strip()
                item_path = (item.get('path') or '').strip()
                if not name or not item_path:
                    continue

                if item_type == 'dir':
                    if name.lower() in ignored_dirs:
                        continue
                    queue.append((item_path, depth + 1))
                elif item_type == 'file':
                    lower = name.lower()
                    if lower.endswith(tuple(exts)):
                        results.append(item_path)
                        if len(results) >= max_files:
                            break

        return results

    def _analyze_repo_contents(self, contents, evidence, repo, username, repo_name):
        """Analyze repository contents for quality indicators"""
        file_names = [item.get('name', '').lower() for item in contents]
        dir_names = [item.get('name', '').lower() for item in contents if item.get('type') == 'dir']
        evidence['directory_count'] = len(dir_names)
        evidence['file_count'] = len(file_names)
        
        # Check for README
        for pattern in self.readme_patterns:
            if pattern.lower() in file_names:
                evidence['has_readme'] = True
                readme_content = self.github_service.fetch_file_content(username, repo_name, pattern)
                if readme_content:
                    readme_eval = self._evaluate_readme_quality(readme_content)
                    evidence['readme_quality'] = readme_eval['label']
                    evidence['readme_quality_score'] = readme_eval['score']
                    evidence['readme_readability'] = readme_eval.get('readability')
                    readme_signals = readme_eval.get('signals', {})
                    evidence['readme_has_installation'] = readme_signals.get('has_installation', False)
                    evidence['readme_has_usage'] = readme_signals.get('has_usage', False)
                    evidence['readme_has_features'] = readme_signals.get('has_features', False)
                break

        # NOTE: Per request, do NOT consider LICENSE/tests/CI-CD signals.
        #
        # # Check for LICENSE
        # for pattern in self.license_patterns:
        #     if pattern.lower() in file_names:
        #         evidence['has_license'] = True
        #         break
        #
        # # Check for tests
        # for name in file_names + dir_names:
        #     for pattern in self.test_patterns:
        #         if pattern.lower() in name.lower():
        #             evidence['has_tests'] = True
        #             evidence['test_coverage_indicator'] = 'present'
        #             evidence['test_signal_count'] += 1
        #             break
        #
        # # Check for CI/CD
        # if '.github' in dir_names:
        #     try:
        #         github_contents = self.github_service.fetch_repository_contents(username, repo_name, '.github')
        #         if github_contents:
        #             gh_files = [f.get('name', '').lower() for f in github_contents]
        #             if 'workflows' in gh_files:
        #                 evidence['has_ci_cd'] = True
        #     except Exception:
        #         pass
        #
        # for pattern in self.ci_patterns:
        #     if pattern.lower().split('/')[0] in file_names:
        #         evidence['has_ci_cd'] = True
        #         break
        
        # Check for documentation
        for pattern in self.doc_patterns:
            if pattern.lower() in dir_names:
                evidence['has_documentation'] = True
                break
        
        # Check for config files
        for pattern in self.config_patterns:
            if pattern.lower() in file_names:
                evidence['has_gitignore'] = True
                break

        # Dependency manifests (good signal for real runnable projects)
        for pattern in self.dependency_patterns:
            if pattern.lower() in file_names:
                evidence['has_dependency_manifest'] = True
                break

        # Environment templates
        for pattern in self.env_patterns:
            if pattern.lower() in file_names:
                evidence['has_env_example'] = True
                break

        # Examples / demo folders
        for pattern in self.example_patterns:
            if pattern.lower() in dir_names or pattern.lower() in file_names:
                evidence['has_examples'] = True
                break

        # Changelog / release notes
        for pattern in self.changelog_patterns:
            if pattern.lower() in file_names:
                evidence['has_changelog'] = True
                break

        # Architecture/design documentation
        for pattern in self.architecture_patterns:
            if pattern.lower() in file_names:
                evidence['has_architecture_doc'] = True
                break
        
        # Check for CONTRIBUTING
        if 'contributing.md' in file_names or 'contributing' in file_names:
            evidence['has_contributing'] = True
        
        # Evaluate code structure
        evidence['code_structure'] = self._evaluate_code_structure(contents, dir_names)
        
        # Analyze commit patterns
        commits = self.github_service.fetch_commits(username, repo_name, per_page=30)
        if commits:
            frequency_eval = self._evaluate_commit_frequency(commits, repo)
            evidence['commit_frequency'] = frequency_eval['label']
            evidence['commit_frequency_score'] = frequency_eval['score']

            message_eval = self._evaluate_commit_messages(commits)
            evidence['commit_message_quality'] = message_eval['label']
            evidence['commit_message_score'] = message_eval['score']
        
        return evidence

    def _evaluate_readme_quality(self, content):
        """Evaluate README quality using structure + readability (textstat if available)."""
        if not content:
            return {'label': 'none', 'score': 0, 'readability': None}
        
        word_count = len(re.findall(r'\b\w+\b', content))
        
        # Check for key sections
        has_installation = bool(re.search(r'(?i)(install|setup|getting started)', content))
        has_usage = bool(re.search(r'(?i)(usage|how to use|example)', content))
        has_features = bool(re.search(r'(?i)(features|what it does)', content))
        has_contributing = bool(re.search(r'(?i)(contribut|development)', content))
        has_badges = bool(re.search(r'\[!\[', content))  # Markdown badges
        has_code_blocks = bool(re.search(r'```', content))
        
        structure_score = 0
        if word_count >= 500:
            structure_score += 35
        elif word_count >= 250:
            structure_score += 25
        elif word_count >= 120:
            structure_score += 15
        elif word_count >= 60:
            structure_score += 8
        
        if has_installation:
            structure_score += 12
        if has_usage:
            structure_score += 12
        if has_features:
            structure_score += 10
        if has_contributing:
            structure_score += 8
        if has_badges:
            structure_score += 5
        if has_code_blocks:
            structure_score += 8

        readability = None
        readability_score = 0
        if textstat:
            try:
                readability = float(textstat.flesch_reading_ease(content))
                if readability >= 60:
                    readability_score = 20
                elif readability >= 40:
                    readability_score = 15
                elif readability >= 25:
                    readability_score = 10
                else:
                    readability_score = 6
            except Exception:
                readability = None

        total_score = self._clamp(structure_score + readability_score, 0, 100)
        
        if total_score >= 80:
            label = 'excellent'
        elif total_score >= 60:
            label = 'good'
        elif total_score >= 35:
            label = 'basic'
        elif total_score > 0:
            label = 'minimal'
        else:
            label = 'none'

        return {
            'label': label,
            'score': round(total_score, 1),
            'readability': readability,
            'signals': {
                'has_installation': has_installation,
                'has_usage': has_usage,
                'has_features': has_features,
                'has_contributing': has_contributing,
                'has_badges': has_badges,
                'has_code_blocks': has_code_blocks
            }
        }

    def _evaluate_code_structure(self, contents, dir_names):
        """Evaluate how well the code is organized"""
        # Check for common good structure patterns
        good_patterns = ['src', 'lib', 'app', 'core', 'utils', 'helpers', 'components', 'services', 'models', 'controllers']
        
        structure_score = 0
        for pattern in good_patterns:
            if pattern in dir_names:
                structure_score += 1
        
        # Check for separation of concerns
        if 'src' in dir_names or 'lib' in dir_names:
            structure_score += 2
        print(structure_score)
        if structure_score >= 4:
            return 'excellent'
        elif structure_score >= 2:
            return 'good'
        elif len(dir_names) > 0:
            return 'basic'
        return 'minimal'

    def _evaluate_commit_frequency(self, commits, repo):
        """Evaluate commit frequency using timeline dynamics from commit dates."""
        if not commits:
            return {'label': 'none', 'score': 0}

        commit_dates = []
        for commit in commits:
            dt = self._parse_datetime(commit.get('date'))
            if dt:
                commit_dates.append(dt)

        if len(commit_dates) < 2:
            # Fallback when commit dates are missing from API payload.
            created_at = self._parse_datetime(repo.get('created_at'))
            if created_at:
                now = datetime.now(created_at.tzinfo or timezone.utc)
                days_old = max((now - created_at).days, 1)
                commits_per_month = (len(commits) / days_old) * 30
                score = self._clamp((commits_per_month ** 0.6) * 18, 0, 100)
                label = 'moderate' if score >= 45 else 'low'
                return {'label': label, 'score': round(score, 1)}
            return {'label': 'unknown', 'score': 20}

        commit_dates.sort(reverse=True)
        now = datetime.now(commit_dates[0].tzinfo or timezone.utc)

        window_days = max((commit_dates[0] - commit_dates[-1]).days, 1)
        commits_per_week = len(commit_dates) / max(window_days / 7.0, 1.0)
        commits_per_month = commits_per_week * 4.345

        recent_30 = sum(1 for dt in commit_dates if (now - dt).days <= 30)
        recency_ratio = recent_30 / max(len(commit_dates), 1)

        intervals = []
        for i in range(len(commit_dates) - 1):
            gap = max((commit_dates[i] - commit_dates[i + 1]).days, 0)
            intervals.append(gap)

        if intervals:
            avg_gap = mean(intervals)
            gap_std = pstdev(intervals) if len(intervals) > 1 else 0
            consistency = 1 - self._clamp(gap_std / max(avg_gap, 1), 0, 1)
        else:
            consistency = 0.5

        volume_score = self._clamp((commits_per_month ** 0.62) * 18, 0, 100)
        recency_score = self._clamp(recency_ratio * 100, 0, 100)
        consistency_score = self._clamp(consistency * 100, 0, 100)
        score = (volume_score * 0.55) + (recency_score * 0.25) + (consistency_score * 0.20)

        if score >= 78:
            label = 'very_active'
        elif score >= 62:
            label = 'active'
        elif score >= 42:
            label = 'moderate'
        else:
            label = 'low'

        return {'label': label, 'score': round(score, 1)}

    def _evaluate_commit_messages(self, commits):
        """Evaluate commit message quality with convention, clarity and anti-repetition signals."""
        if not commits:
            return {'label': 'none', 'score': 0}
        
        first_lines = []
        quality_points = []
        for commit in commits:
            message = commit.get('message', '')
            first_line = message.split('\n')[0] if message else ''
            if first_line:
                first_lines.append(first_line)
            
            # Good commit: 10-72 chars, starts with capital or conventional commit prefix
            is_good_length = 10 <= len(first_line) <= 72
            has_conventional = bool(re.match(r'^(feat|fix|docs|style|refactor|test|chore|build|ci|perf|revert)(\(.+\))?:', first_line, re.IGNORECASE))
            starts_with_capital = first_line and first_line[0].isupper()
            has_issue_ref = bool(re.search(r'(#\d+|[A-Z]+-\d+)', first_line))
            is_noisy = bool(re.search(r'(?i)^(update|changes|misc|test)$', first_line.strip()))
            has_verb = bool(re.match(r'(?i)^(add|fix|refactor|update|remove|improve|implement|create|optimize|docs?)\b', first_line.strip()))
            
            score = 0
            if is_good_length:
                score += 35
            if has_conventional:
                score += 30
            elif starts_with_capital:
                score += 20
            if has_issue_ref:
                score += 10
            if has_verb:
                score += 8
            if is_noisy:
                score -= 20
            quality_points.append(self._clamp(score, 0, 100))
        
        avg_score = mean(quality_points) if quality_points else 0

        # Penalize repetitive commit messages with rapidfuzz when available.
        repetition_penalty = self._compute_repetition_penalty(first_lines)
        avg_score = self._clamp(avg_score - repetition_penalty, 0, 100)
        
        if avg_score >= 75:
            label = 'excellent'
        elif avg_score >= 58:
            label = 'good'
        elif avg_score >= 40:
            label = 'average'
        else:
            label = 'poor'

        return {'label': label, 'score': round(avg_score, 1)}

    def _compute_repetition_penalty(self, messages):
        """Compute penalty for repeated / near-duplicate commit messages."""
        cleaned = [m.strip().lower() for m in messages if m and m.strip()]
        if len(cleaned) < 3:
            return 0

        # Exact-duplicate signal.
        unique_ratio = len(set(cleaned)) / len(cleaned)
        exact_dup_penalty = (1 - unique_ratio) * 22

        # Near-duplicate signal via rapidfuzz (fallback to exact duplicates only).
        near_dup_penalty = 0
        if fuzz:
            pair_scores = []
            sample_cap = min(len(cleaned), 20)
            for i in range(sample_cap):
                for j in range(i + 1, sample_cap):
                    pair_scores.append(fuzz.ratio(cleaned[i], cleaned[j]))
            if pair_scores:
                high_similarity_ratio = sum(1 for s in pair_scores if s >= 88) / len(pair_scores)
                near_dup_penalty = high_similarity_ratio * 18

        return round(self._clamp(exact_dup_penalty + near_dup_penalty, 0, 28), 1)

    def _calculate_category_scores(self, evidence, repo):
        scores = {}
        
        # Documentation Score (0-100)
        doc_score = 0
        if evidence['has_readme']:
            doc_score += evidence.get('readme_quality_score', 0) * 0.65
        if evidence['has_documentation']:
            doc_score += 18
        if evidence.get('has_architecture_doc'):
            doc_score += 10
        if evidence.get('has_examples'):
            doc_score += 10
        if evidence.get('readme_has_usage'):
            doc_score += 7
        if evidence['has_contributing']:
            doc_score += 10
        # NOTE: license signal excluded per request.
        # if evidence['has_license']:
        #     doc_score += 4
        scores['documentation'] = round(self._clamp(doc_score, 0, 100), 1)

        # NOTE: excluded per request (only: code health, documentation, commit quality, code organization)
        #
        # # Testing/Verification Score (0-100)
        # # For portfolio analysis, emphasize runnable/readable project signals over enterprise process.
        # test_score = 0
        # if evidence.get('has_dependency_manifest'):
        #     test_score += 30
        # if evidence.get('readme_has_installation'):
        #     test_score += 24
        # if evidence.get('readme_has_usage'):
        #     test_score += 18
        # if evidence.get('has_examples'):
        #     test_score += 12
        # if evidence.get('has_env_example'):
        #     test_score += 8
        # if evidence.get('has_changelog'):
        #     test_score += 5
        # if evidence.get('has_architecture_doc'):
        #     test_score += 5
        # if evidence.get('readme_has_features'):
        #     test_score += 4
        # # scores['testing'] = round(self._clamp(test_score, 0, 100), 1)
        
        # Code Organization Score (0-100)
        org_scores = {'excellent': 100, 'good': 75, 'basic': 50, 'minimal': 25}
        structure_base = org_scores.get(evidence['code_structure'], 25)
        richness_bonus = min(15, evidence.get('directory_count', 0) * 1.5)
        scores['code_organization'] = round(self._clamp(structure_base * 0.85 + richness_bonus, 0, 100), 1)
        
        # NOTE: excluded per request (only: code health, documentation, commit quality, code organization)
        #
        # # Maintainability Score (0-100)
        # maintain_score = 0
        # if evidence['has_gitignore']:
        #     maintain_score += 25
        # if evidence['has_readme']:
        #     maintain_score += 25
        # if evidence.get('has_dependency_manifest'):
        #     maintain_score += 20
        # if evidence['code_structure'] in ['excellent', 'good']:
        #     maintain_score += 20
        # if evidence.get('has_changelog'):
        #     maintain_score += 10
        # if evidence.get('has_env_example'):
        #     maintain_score += 10
        # # Keep these as lightweight bonuses.
        # if evidence['has_license']:
        #     maintain_score += 5
        # # scores['maintainability'] = round(self._clamp(maintain_score, 0, 100), 1)
        
        # Commit Quality Score (0-100)
        commit_score = (evidence.get('commit_frequency_score', 0) * 0.45) + (evidence.get('commit_message_score', 0) * 0.55)
        scores['commit_quality'] = round(self._clamp(commit_score, 0, 100), 1)
        
        return scores

    def _calculate_weighted_score(self, scores, repos):
        """Calculate weighted average score based on repo importance"""
        if not scores:
            return 0
        
        # Weight by stars + recency (important and active repos count more).
        weights = []
        for repo in repos:
            stars = repo.get('stars', 0)
            recency_bonus = self._recency_weight(repo.get('pushed_at') or repo.get('updated_at'))
            weight = 1 + (stars * 0.08) + recency_bonus
            weights.append(min(weight, 5))  # Cap at 5x
        
        weighted_sum = sum(s * w for s, w in zip(scores, weights))
        total_weight = sum(weights)
        
        if total_weight <= 0:
            return 0
        return self._clamp(weighted_sum / total_weight, 0, 100)

    def _score_to_grade(self, score, dynamic_thresholds=None):
        """Convert numeric score to letter grade with optional dynamic thresholds."""
        thresholds = dynamic_thresholds or self.grade_thresholds
        for grade, threshold in thresholds.items():
            if score >= threshold:
                return grade
        return 'F'

    def _get_grade_label(self, grade):
        """Get descriptive label for grade"""
        labels = {
            'A': 'Excellent',
            'B': 'Good',
            'C': 'Average',
            'D': 'Below Average',
            'F': 'Needs Improvement'
        }
        return labels.get(grade, 'Unknown')

    def _aggregate_metrics(self, detailed_analysis):
        """Aggregate metrics across all analyzed repos"""
        if not detailed_analysis:
            return {}
        
        metrics = {
            'repos_with_readme': 0,
            'repos_with_docs': 0,
            'avg_documentation_score': 0,
            'avg_code_organization_score': 0,
            'avg_commit_quality_score': 0,
            'avg_code_health_score': None,
            'code_health_repos_analyzed': 0,
            'code_health_files_analyzed': 0,
            'code_health_language': None,
            'code_health_languages': [],
        }

        code_health_language_counts = {}
        
        total_repos = len(detailed_analysis)
        
        for repo in detailed_analysis:
            evidence = repo.get('evidence', {})
            scores = repo.get('scores', {})
            
            if evidence.get('has_readme'):
                metrics['repos_with_readme'] += 1
            # NOTE: excluded per request.
            # if evidence.get('has_tests'):
            #     metrics['repos_with_tests'] += 1
            # if evidence.get('has_ci_cd'):
            #     metrics['repos_with_ci_cd'] += 1
            # readiness_signal_count = sum([
            #     1 if evidence.get('has_dependency_manifest') else 0,
            #     1 if evidence.get('readme_has_installation') else 0,
            #     1 if evidence.get('readme_has_usage') else 0,
            #     1 if evidence.get('has_examples') else 0,
            #     1 if evidence.get('has_env_example') else 0,
            # ])
            # if readiness_signal_count >= 2:
            #     metrics['repos_with_readiness_signals'] += 1
            # if evidence.get('has_license'):
            #     metrics['repos_with_license'] += 1
            if evidence.get('has_documentation'):
                metrics['repos_with_docs'] += 1
            
            metrics['avg_documentation_score'] += scores.get('documentation', 0)
            metrics['avg_code_organization_score'] += scores.get('code_organization', 0)
            metrics['avg_commit_quality_score'] += scores.get('commit_quality', 0)

            if evidence.get('code_health_available') and scores.get('code_health') is not None:
                if metrics['avg_code_health_score'] is None:
                    metrics['avg_code_health_score'] = 0
                metrics['avg_code_health_score'] += float(scores.get('code_health') or 0)
                metrics['code_health_repos_analyzed'] += 1
                metrics['code_health_files_analyzed'] += int(evidence.get('code_health_files_analyzed', 0) or 0)

                langs = evidence.get('code_health_languages')
                if not isinstance(langs, list) or not langs:
                    # Backward-compat fallback (older evidence stored only a single language).
                    lang = (evidence.get('code_health_language') or '').strip()
                    langs = [lang] if lang else []

                for lang in langs:
                    if not lang:
                        continue
                    lang = str(lang).strip()
                    if not lang or lang.lower() == 'mixed':
                        continue
                    code_health_language_counts[lang] = int(code_health_language_counts.get(lang, 0)) + 1
        
        # Calculate averages
        for key in metrics:
            if key.startswith('avg_'):
                if key == 'avg_code_health_score':
                    if metrics['code_health_repos_analyzed'] > 0:
                        metrics[key] = round(
                            self._clamp(metrics[key] / metrics['code_health_repos_analyzed'], 0, 100),
                            1
                        )
                    else:
                        metrics[key] = None
                else:
                    metrics[key] = round(self._clamp(metrics[key] / total_repos, 0, 100), 1)
        
        # Add percentages
        metrics['readme_percentage'] = round(self._clamp((metrics['repos_with_readme'] / total_repos) * 100, 0, 100), 1)
        # NOTE: excluded per request.
        # metrics['readiness_percentage'] = round(self._clamp((metrics['repos_with_readiness_signals'] / total_repos) * 100, 0, 100), 1)
        # # Backward-compatible alias kept for existing frontend/API consumers.
        # metrics['testing_percentage'] = metrics['readiness_percentage']
        # metrics['ci_cd_percentage'] = round(self._clamp((metrics['repos_with_ci_cd'] / total_repos) * 100, 0, 100), 1)

        if code_health_language_counts:
            languages_sorted = sorted(
                code_health_language_counts.items(),
                key=lambda kv: (int(kv[1] or 0), str(kv[0] or '')),
                reverse=True,
            )
            metrics['code_health_languages'] = [lang for lang, _ in languages_sorted]
            if len(metrics['code_health_languages']) == 1:
                metrics['code_health_language'] = metrics['code_health_languages'][0]
            else:
                # Mixed portfolio: multiple languages contributed code-health analysis.
                metrics['code_health_language'] = 'Mixed'
        
        return metrics

    def _generate_suggestions(self, metrics, detailed_analysis):
        """Generate improvement suggestions based on analysis"""
        suggestions = []
        
        if metrics.get('readme_percentage', 0) < 70:
            suggestions.append({
                'category': 'Documentation',
                'priority': 'high',
                'suggestion': 'Add comprehensive README files to all repositories',
                'impact': 'Improves project understanding and collaboration'
            })
        
        # NOTE: excluded per request.
        # if metrics.get('readiness_percentage', metrics.get('testing_percentage', 0)) < 45:
        #     suggestions.append({
        #         'category': 'Project Readiness',
        #         'priority': 'high',
        #         'suggestion': 'Improve delivery readiness with setup, usage examples, and reproducible project instructions',
        #         'impact': 'Helps reviewers run and trust your projects quickly'
        #     })
        #
        # if metrics.get('avg_maintainability_score', 0) < 55:
        #     suggestions.append({
        #         'category': 'Maintainability',
        #         'priority': 'medium',
        #         'suggestion': 'Improve maintainability with cleaner project setup and clearer structure',
        #         'impact': 'Makes projects easier to evolve and review'
        #     })
        
        if metrics.get('avg_code_organization_score', 0) < 55:
            suggestions.append({
                'category': 'Code Organization',
                'priority': 'medium',
                'suggestion': 'Organize code into clear directories (src/, lib/, etc.)',
                'impact': 'Improves code maintainability and readability'
            })
        
        if metrics.get('avg_commit_quality_score', 0) < 45:
            suggestions.append({
                'category': 'Commit Practices',
                'priority': 'low',
                'suggestion': 'Use clearer commit messages and avoid repetitive commit titles',
                'impact': 'Shows better development discipline and project evolution'
            })

        if metrics.get('avg_code_health_score') is not None and metrics.get('avg_code_health_score', 0) < 55:
            suggestions.append({
                'category': 'Code Quality',
                'priority': 'medium',
                'suggestion': 'Reduce complex functions and improve maintainability (e.g., split long functions, simplify branching)',
                'impact': 'Improves actual code maintainability and readability'
            })
        
        return suggestions

    def _identify_strengths(self, metrics):
        """Identify areas where the candidate excels"""
        strengths = []
        
        if metrics.get('avg_documentation_score', 0) >= 70:
            strengths.append({
                'area': 'Documentation',
                'description': 'Well-documented projects with comprehensive READMEs'
            })
        
        # NOTE: excluded per request.
        # if metrics.get('avg_testing_score', 0) >= 60:
        #     strengths.append({
        #         'area': 'Project Readiness',
        #         'description': 'Projects include strong setup/run instructions and reproducible delivery signals'
        #     })
        
        if metrics.get('avg_code_organization_score', 0) >= 75:
            strengths.append({
                'area': 'Code Organization',
                'description': 'Well-structured and organized codebases'
            })
        
        if metrics.get('avg_commit_quality_score', 0) >= 70:
            strengths.append({
                'area': 'Version Control',
                'description': 'Professional commit practices and active development'
            })

        if metrics.get('avg_code_health_score') is not None and metrics.get('avg_code_health_score', 0) >= 70:
            strengths.append({
                'area': 'Code Quality',
                'description': 'Low-complexity, maintainable code in analyzed files'
            })
        
        return strengths

    def _identify_weaknesses(self, metrics):
        """Identify areas that need improvement"""
        weaknesses = []
        
        if metrics.get('avg_documentation_score', 0) < 40:
            weaknesses.append({
                'area': 'Documentation',
                'description': 'Projects lack proper documentation'
            })
        
        # NOTE: excluded per request.
        # if metrics.get('avg_testing_score', 0) < 30:
        #     weaknesses.append({
        #         'area': 'Project Readiness',
        #         'description': 'Projects need clearer setup, usage, and reproducibility instructions'
        #     })
        #
        # if metrics.get('avg_maintainability_score', 0) < 45:
        #     weaknesses.append({
        #         'area': 'Maintainability',
        #         'description': 'Project maintenance and structure quality can be improved'
        #     })
        
        if metrics.get('avg_code_organization_score', 0) < 50:
            weaknesses.append({
                'area': 'Code Organization',
                'description': 'Code structure could be improved'
            })

        if metrics.get('avg_code_health_score') is not None and metrics.get('avg_code_health_score', 0) < 45:
            weaknesses.append({
                'area': 'Code Quality',
                'description': 'Some analyzed code appears complex and harder to maintain'
            })
        
        return weaknesses

    def _to_timestamp(self, dt_str):
        dt = self._parse_datetime(dt_str)
        return dt.timestamp() if dt else 0

    def _parse_datetime(self, dt_str):
        if not dt_str:
            return None
        try:
            if date_parser:
                return date_parser.isoparse(dt_str)
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except Exception:
            return None

    def _recency_weight(self, dt_str):
        dt = self._parse_datetime(dt_str)
        if not dt:
            return 0
        now = datetime.now(dt.tzinfo or timezone.utc)
        days = max((now - dt).days, 0)
        if days <= 30:
            return 1.0
        if days <= 90:
            return 0.6
        if days <= 180:
            return 0.3
        return 0

    def _derive_dynamic_thresholds(self, calibrated_scores):
        """Build adaptive grade thresholds from repository score distribution."""
        if not calibrated_scores:
            return self.grade_thresholds.copy()

        avg = mean(calibrated_scores)
        std = pstdev(calibrated_scores) if len(calibrated_scores) > 1 else 8
        std = max(std, 6)

        thresholds = {
            'A': self._clamp(avg + (0.9 * std), 78, 90),
            'B': self._clamp(avg + (0.2 * std), 64, 80),
            'C': self._clamp(avg - (0.5 * std), 50, 66),
            'D': self._clamp(avg - (1.1 * std), 35, 55),
            'F': 0
        }

        # Ensure monotonic descending thresholds.
        thresholds['B'] = min(thresholds['B'], thresholds['A'] - 5)
        thresholds['C'] = min(thresholds['C'], thresholds['B'] - 5)
        thresholds['D'] = min(thresholds['D'], thresholds['C'] - 5)
        return {k: round(v, 1) if k != 'F' else v for k, v in thresholds.items()}

    def _apply_dynamic_calibration(self, detailed_analysis):
        """Calibrate strictness by blending raw scores with portfolio-relative z-score scaling."""
        if not detailed_analysis:
            return

        raw_scores = [repo.get('score', 0) for repo in detailed_analysis]
        avg = mean(raw_scores)
        std = pstdev(raw_scores) if len(raw_scores) > 1 else 10
        std = max(std, 8)

        for repo in detailed_analysis:
            raw = repo.get('score', 0)
            z_scaled = 50 + ((raw - avg) / std) * 15
            # Blend keeps absolute scoring while preventing overly harsh penalties.
            calibrated = (raw * 0.75) + (z_scaled * 0.25) + 3
            calibrated = round(self._clamp(calibrated, 0, 100), 1)
            repo['score_raw'] = round(raw, 1)
            repo['score'] = calibrated

    def _clamp(self, value, low, high):
        return max(low, min(high, value))
