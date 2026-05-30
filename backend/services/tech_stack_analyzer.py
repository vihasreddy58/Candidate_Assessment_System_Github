import re
import json
from datetime import datetime, timedelta


class TechStackAnalyzer:
    def __init__(self, github_service):
        self.github_service = github_service
        
        self.tech_patterns = {
            # Frontend Frameworks
            'React': {
                'patterns': [r'import.*from\s+[\'"]react[\'"]', r'require\([\'"]react[\'"]\)'],
                'files': ['package.json'],
                'package_names': ['react', 'react-dom'],
                'file_extensions': ['.jsx', '.tsx']
            },
            'Vue.js': {
                'patterns': [r'import.*from\s+[\'"]vue[\'"]', r'require\([\'"]vue[\'"]\)'],
                'files': ['package.json', 'vue.config.js'],
                'package_names': ['vue', '@vue/cli']
            },
            'Angular': {
                'patterns': [r'import.*from\s+[\'"]@angular'],
                'files': ['package.json', 'angular.json'],
                'package_names': ['@angular/core']
            },
            'Next.js': {
                'patterns': [r'import.*from\s+[\'"]next[\'"]'],
                'files': ['next.config.js', 'package.json'],
                'package_names': ['next']
            },
            'Svelte': {
                'patterns': [],
                'files': ['package.json', 'svelte.config.js'],
                'package_names': ['svelte'],
                'file_extensions': ['.svelte']
            },
            # Backend Frameworks
            'Express': {
                'patterns': [r'require\([\'"]express[\'"]\)', r'import.*from\s+[\'"]express[\'"]', r'express\(\)'],
                'files': ['package.json'],
                'package_names': ['express']
            },
            'NestJS': {
                'patterns': [r'import.*from\s+[\'"]@nestjs'],
                'files': ['nest-cli.json', 'package.json'],
                'package_names': ['@nestjs/core']
            },
            'Django': {
                'patterns': [r'from\s+django', r'import\s+django'],
                'files': ['manage.py', 'requirements.txt', 'pyproject.toml'],
                'package_names': ['django', 'Django']
            },
            'Flask': {
                'patterns': [r'from\s+flask\s+import', r'import\s+flask'],
                'files': ['requirements.txt', 'pyproject.toml'],
                'package_names': ['flask', 'Flask']
            },
            'FastAPI': {
                'patterns': [r'from\s+fastapi\s+import', r'import\s+fastapi'],
                'files': ['requirements.txt', 'pyproject.toml'],
                'package_names': ['fastapi']
            },
            'Spring Boot': {
                'patterns': [r'@SpringBootApplication'],
                'files': ['pom.xml', 'build.gradle'],
                'package_names': ['spring-boot-starter']
            },
            # Databases
            'MongoDB': {
                'patterns': [r'require\([\'"]mongodb[\'"]\)', r'import.*from\s+[\'"]mongodb[\'"]', r'mongoose'],
                'files': ['package.json', 'requirements.txt'],
                'package_names': ['mongodb', 'mongoose', 'pymongo']
            },
            'PostgreSQL': {
                'patterns': [r'pg\.', r'psycopg2'],
                'files': ['package.json', 'requirements.txt'],
                'package_names': ['pg', 'postgres', 'psycopg2']
            },
            'MySQL': {
                'patterns': [r'mysql'],
                'files': ['package.json', 'requirements.txt', 'pom.xml'],
                'package_names': ['mysql', 'mysql2', 'pymysql']
            },
            'Redis': {
                'patterns': [r'redis'],
                'files': ['package.json', 'requirements.txt'],
                'package_names': ['redis', 'ioredis']
            },
            # Cloud & DevOps
            'Docker': {
                'patterns': [],
                'files': ['Dockerfile', 'docker-compose.yml', '.dockerignore']
            },
            'Kubernetes': {
                'patterns': [],
                'files': ['k8s/', 'kubernetes/', 'deployment.yaml', 'service.yaml']
            },
            'AWS': {
                'patterns': [r'aws-sdk', r'boto3'],
                'files': ['package.json', 'requirements.txt'],
                'package_names': ['aws-sdk', 'boto3', '@aws-sdk']
            },
            # Testing
            'Jest': {
                'patterns': [r'describe\(', r'test\(', r'it\('],
                'files': ['jest.config.js', 'package.json'],
                'package_names': ['jest']
            },
            'Pytest': {
                'patterns': [r'def\s+test_', r'@pytest'],
                'files': ['pytest.ini', 'requirements.txt'],
                'package_names': ['pytest']
            },
            # Data Science & ML
            'TensorFlow': {
                'patterns': [r'import\s+tensorflow', r'from\s+tensorflow'],
                'files': ['requirements.txt', 'pyproject.toml'],
                'package_names': ['tensorflow']
            },
            'PyTorch': {
                'patterns': [r'import\s+torch', r'from\s+torch'],
                'files': ['requirements.txt', 'pyproject.toml'],
                'package_names': ['torch', 'pytorch']
            },
            'Pandas': {
                'patterns': [r'import\s+pandas', r'import\s+pandas\s+as\s+pd'],
                'files': ['requirements.txt', 'pyproject.toml'],
                'package_names': ['pandas']
            },
            'NumPy': {
                'patterns': [r'import\s+numpy', r'import\s+numpy\s+as\s+np'],
                'files': ['requirements.txt', 'pyproject.toml'],
                'package_names': ['numpy']
            },
            'Scikit-learn': {
                'patterns': [r'from\s+sklearn'],
                'files': ['requirements.txt', 'pyproject.toml'],
                'package_names': ['scikit-learn', 'sklearn']
            },
            # Build Tools
            'Webpack': {
                'patterns': [],
                'files': ['webpack.config.js', 'package.json'],
                'package_names': ['webpack']
            },
            'Vite': {
                'patterns': [],
                'files': ['vite.config.js', 'vite.config.ts', 'package.json'],
                'package_names': ['vite']
            },
            'TypeScript': {
                'patterns': [],
                'files': ['tsconfig.json', 'package.json'],
                'package_names': ['typescript'],
                'file_extensions': ['.ts', '.tsx']
            },
            'GraphQL': {
                'patterns': [r'graphql', r'apollo'],
                'files': ['package.json'],
                'package_names': ['graphql', 'apollo-server', '@apollo/client']
            },
            'Tailwind CSS': {
                'patterns': [r'@tailwind'],
                'files': ['tailwind.config.js', 'package.json'],
                'package_names': ['tailwindcss']
            }
        }

    def analyze_repositories(self, repositories):
        print(f"Analyzing {len(repositories)} repositories...")
        
        detected_skills = {}
        repo_details = []

        repos_to_analyze = self._select_repositories_to_analyze(repositories)
        print(f"Deep analyzing {len(repos_to_analyze)} repositories")

        for repo in repos_to_analyze:
            repo_analysis = self._analyze_repository(repo)
            repo_details.append(repo_analysis)

            for skill, data in repo_analysis['detected_technologies'].items():
                if skill not in detected_skills:
                    detected_skills[skill] = {
                        'count': 0,
                        'confidence': 0,
                        'repositories': [],
                        'evidence': []
                    }

                detected_skills[skill]['count'] += 1
                detected_skills[skill]['repositories'].append(repo['name'])
                detected_skills[skill]['evidence'].extend(data.get('evidence', []))
                detected_skills[skill]['confidence'] = max(
                    detected_skills[skill]['confidence'],
                    data.get('confidence', 0)
                )

        # Calculate usage frequency
        for skill in detected_skills:
            detected_skills[skill]['usageFrequency'] = round(
                (detected_skills[skill]['count'] / len(repos_to_analyze)) * 100, 2
            ) if repos_to_analyze else 0

        return {
            'detected_skills': detected_skills,
            'repo_details': repo_details,
            'total_repos_analyzed': len(repos_to_analyze)
        }

    def _select_repositories_to_analyze(self, repositories):
        # Filter out forks
        original_repos = [r for r in repositories if not r.get('is_fork')]
        
        # Sort by stars and recency
        def score_repo(repo):
            try:
                updated = datetime.fromisoformat(repo.get('updated_at', '').replace('Z', '+00:00'))
                days_since = (datetime.now(updated.tzinfo) - updated).days
                recency_score = max(0, 365 - days_since)
            except:
                recency_score = 0
            star_score = repo.get('stars', 0) * 10
            return recency_score + star_score

        sorted_repos = sorted(original_repos, key=score_repo, reverse=True)
        return sorted_repos[:50]  # Analyze up to 50 repos

    def _analyze_repository(self, repo):
        print(f"  Analyzing {repo['name']}...")
        
        username = repo['full_name'].split('/')[0]
        detected_technologies = {}

        # Primary language detection
        if repo.get('language'):
            detected_technologies[repo['language']] = {
                'confidence': 90,
                'evidence': ['Primary repository language'],
                'type': 'language'
            }

        try:
            # Fetch root contents
            contents = self.github_service.fetch_repository_contents(username, repo['name'])
            
            # Check for files recursively
            all_files = self._get_all_files_recursive(username, repo['name'], contents, max_depth=3)
            
            # Detect technologies from files
            self._detect_from_files(all_files, detected_technologies, username, repo['name'])
            
            # Always add Git since it's a GitHub repo
            detected_technologies['Git'] = {
                'confidence': 100,
                'evidence': ['Repository hosted on GitHub'],
                'type': 'tool'
            }

        except Exception as e:
            print(f"    Could not fully analyze {repo['name']}: {str(e)}")

        return {
            'name': repo['name'],
            'stars': repo.get('stars', 0),
            'language': repo.get('language'),
            'detected_technologies': detected_technologies,
            'updated_at': repo.get('updated_at')
        }

    def _get_all_files_recursive(self, username, repo_name, contents, path='', max_depth=3, current_depth=0):
        """Recursively get all files in the repository"""
        all_files = []
        
        if current_depth > max_depth:
            return all_files
            
        for item in contents:
            if item.get('type') == 'file':
                all_files.append({
                    'name': item.get('name', ''),
                    'path': item.get('path', ''),
                    'type': 'file'
                })
            elif item.get('type') == 'dir' and current_depth < max_depth:
                # Skip common non-source directories
                dir_name = item.get('name', '').lower()
                skip_dirs = ['node_modules', 'vendor', 'dist', 'build', '.git', '__pycache__', 'venv', '.venv']
                if dir_name not in skip_dirs:
                    try:
                        sub_contents = self.github_service.fetch_repository_contents(
                            username, repo_name, item.get('path', '')
                        )
                        sub_files = self._get_all_files_recursive(
                            username, repo_name, sub_contents, 
                            item.get('path', ''), max_depth, current_depth + 1
                        )
                        all_files.extend(sub_files)
                    except:
                        pass
        
        return all_files

    def _detect_from_files(self, all_files, detected_technologies, username, repo_name):
        """Detect technologies from file list"""
        file_names = [f['name'].lower() for f in all_files]
        file_paths = [f['path'].lower() for f in all_files]
        
        # Count file types
        html_files = [f for f in all_files if f['name'].endswith('.html')]
        css_files = [f for f in all_files if f['name'].endswith('.css')]
        scss_files = [f for f in all_files if f['name'].endswith('.scss') or f['name'].endswith('.sass')]
        js_files = [f for f in all_files if f['name'].endswith('.js') or f['name'].endswith('.jsx')]
        ts_files = [f for f in all_files if f['name'].endswith('.ts') or f['name'].endswith('.tsx')]
        py_files = [f for f in all_files if f['name'].endswith('.py')]
        java_files = [f for f in all_files if f['name'].endswith('.java')]
        ipynb_files = [f for f in all_files if f['name'].endswith('.ipynb')]
        
        # Detect HTML
        if html_files:
            detected_technologies['HTML'] = {
                'confidence': 95,
                'evidence': [f"{len(html_files)} HTML file(s) found: {', '.join([f['name'] for f in html_files[:3]])}"],
                'type': 'language'
            }
        
        # Detect CSS - IMPROVED: Now checks recursively
        if css_files:
            detected_technologies['CSS'] = {
                'confidence': 95,
                'evidence': [f"{len(css_files)} CSS file(s) found: {', '.join([f['path'] for f in css_files[:3]])}"],
                'type': 'language'
            }
        
        # Detect SCSS/SASS
        if scss_files:
            if 'CSS' not in detected_technologies:
                detected_technologies['CSS'] = {
                    'confidence': 90,
                    'evidence': [],
                    'type': 'language'
                }
            detected_technologies['CSS']['evidence'].append(f"{len(scss_files)} SCSS/SASS file(s) found")
            detected_technologies['SASS'] = {
                'confidence': 95,
                'evidence': [f"{len(scss_files)} SCSS/SASS file(s) found"],
                'type': 'language'
            }
        
        # Detect JavaScript
        if js_files and 'JavaScript' not in detected_technologies:
            detected_technologies['JavaScript'] = {
                'confidence': 90,
                'evidence': [f"{len(js_files)} JavaScript file(s) found"],
                'type': 'language'
            }
        
        # Detect TypeScript
        if ts_files:
            detected_technologies['TypeScript'] = {
                'confidence': 95,
                'evidence': [f"{len(ts_files)} TypeScript file(s) found"],
                'type': 'language'
            }
        
        # Detect Python
        if py_files and 'Python' not in detected_technologies:
            detected_technologies['Python'] = {
                'confidence': 90,
                'evidence': [f"{len(py_files)} Python file(s) found"],
                'type': 'language'
            }
        
        # Detect Java
        if java_files and 'Java' not in detected_technologies:
            detected_technologies['Java'] = {
                'confidence': 90,
                'evidence': [f"{len(java_files)} Java file(s) found"],
                'type': 'language'
            }
        
        # Detect Jupyter notebooks
        if ipynb_files:
            detected_technologies['Jupyter'] = {
                'confidence': 95,
                'evidence': [f"{len(ipynb_files)} Jupyter notebook(s) found"],
                'type': 'tool'
            }
        
        # Check for JSX files (React)
        jsx_files = [f for f in all_files if f['name'].endswith('.jsx')]
        if jsx_files:
            detected_technologies['React'] = {
                'confidence': 85,
                'evidence': [f"{len(jsx_files)} JSX file(s) found"],
                'type': 'framework'
            }
        
        # Check for Vue files
        vue_files = [f for f in all_files if f['name'].endswith('.vue')]
        if vue_files:
            detected_technologies['Vue.js'] = {
                'confidence': 95,
                'evidence': [f"{len(vue_files)} Vue component(s) found"],
                'type': 'framework'
            }
        
        # Check for config files
        for tech, config in self.tech_patterns.items():
            if 'files' in config:
                for config_file in config.get('files', []):
                    if config_file.lower() in file_names:
                        if tech not in detected_technologies:
                            detected_technologies[tech] = {
                                'confidence': 80,
                                'evidence': [],
                                'type': 'framework'
                            }
                        detected_technologies[tech]['evidence'].append(f"Config file: {config_file}")

        # Analyze package.json if present
        if 'package.json' in file_names:
            self._analyze_package_json(detected_technologies, username, repo_name)
        
        # Analyze requirements.txt if present
        if 'requirements.txt' in file_names:
            self._analyze_requirements_txt(detected_technologies, username, repo_name)

    def _analyze_package_json(self, detected_technologies, username, repo_name):
        try:
            content = self.github_service.fetch_file_content(username, repo_name, 'package.json')
            if not content:
                return
            
            pkg = json.loads(content)
            all_deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}

            # Node.js detection
            detected_technologies['Node.js'] = {
                'confidence': 95,
                'evidence': ['package.json present (Node.js project)'],
                'type': 'runtime'
            }

            # Check for packages
            for tech, config in self.tech_patterns.items():
                for pkg_name in config.get('package_names', []):
                    for dep in all_deps:
                        if pkg_name in dep or dep in pkg_name:
                            if tech not in detected_technologies:
                                detected_technologies[tech] = {
                                    'confidence': 95,
                                    'evidence': [],
                                    'type': 'framework'
                                }
                            detected_technologies[tech]['evidence'].append(f"package.json: {dep}")
                            break

            # REST API detection
            rest_packages = ['express', 'koa', 'fastify', 'axios', 'restify', 'hapi']
            for pkg_name in rest_packages:
                if any(pkg_name in dep for dep in all_deps):
                    detected_technologies['REST APIs'] = {
                        'confidence': 90,
                        'evidence': [f'REST API package found'],
                        'type': 'concept'
                    }
                    break

        except Exception as e:
            print(f"    Error parsing package.json: {e}")

    def _analyze_requirements_txt(self, detected_technologies, username, repo_name):
        try:
            content = self.github_service.fetch_file_content(username, repo_name, 'requirements.txt')
            if not content:
                return

            lines = content.split('\n')
            packages = []
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                pkg = re.split(r'[=<>!\[]', line)[0].strip().lower()
                packages.append(pkg)

            # Check specific packages
            package_tech_map = {
                'flask': ('Flask', 'framework'),
                'django': ('Django', 'framework'),
                'fastapi': ('FastAPI', 'framework'),
                'tensorflow': ('TensorFlow', 'library'),
                'torch': ('PyTorch', 'library'),
                'pytorch': ('PyTorch', 'library'),
                'pandas': ('Pandas', 'library'),
                'numpy': ('NumPy', 'library'),
                'scikit-learn': ('Scikit-learn', 'library'),
                'sklearn': ('Scikit-learn', 'library'),
                'keras': ('Keras', 'library'),
                'pytest': ('Pytest', 'testing'),
                'requests': ('REST APIs', 'concept'),
            }

            for pkg in packages:
                for pkg_pattern, (tech, tech_type) in package_tech_map.items():
                    if pkg_pattern in pkg:
                        if tech not in detected_technologies:
                            detected_technologies[tech] = {
                                'confidence': 95,
                                'evidence': [],
                                'type': tech_type
                            }
                        detected_technologies[tech]['evidence'].append(f"requirements.txt: {pkg}")

        except Exception as e:
            print(f"    Error parsing requirements.txt: {e}")
