import re


class SkillMatcher:
    def __init__(self):
        self.skill_canonical_map = {
            # Node.js variations
            'nodejs': 'Node.js', 'node.js': 'Node.js', 'node': 'Node.js',
            # React variations
            'react': 'React', 'reactjs': 'React', 'react.js': 'React',
            # Vue variations
            'vue': 'Vue.js', 'vue.js': 'Vue.js', 'vuejs': 'Vue.js',
            # Angular variations
            'angular': 'Angular', 'angularjs': 'Angular', 'angular.js': 'Angular',
            # MongoDB variations
            'mongodb': 'MongoDB', 'mongo': 'MongoDB', 'mongo db': 'MongoDB',
            # PostgreSQL variations
            'postgresql': 'PostgreSQL', 'postgres': 'PostgreSQL', 'psql': 'PostgreSQL',
            # MySQL variations
            'mysql': 'MySQL',
            # JavaScript variations
            'javascript': 'JavaScript', 'js': 'JavaScript', 'ecmascript': 'JavaScript',
            # TypeScript variations
            'typescript': 'TypeScript', 'ts': 'TypeScript',
            # Python variations
            'python': 'Python', 'python3': 'Python',
            # Docker variations
            'docker': 'Docker', 'containers': 'Docker',
            # Kubernetes variations
            'kubernetes': 'Kubernetes', 'k8s': 'Kubernetes',
            # AWS variations
            'aws': 'AWS', 'amazon web services': 'AWS', 'amazon aws': 'AWS',
            # GCP variations
            'gcp': 'GCP', 'google cloud': 'GCP', 'google cloud platform': 'GCP',
            # Azure variations
            'azure': 'Azure', 'microsoft azure': 'Azure', 'ms azure': 'Azure',
            # Machine Learning variations
            'machine learning': 'Machine Learning', 'ml': 'Machine Learning',
            # AI variations
            'artificial intelligence': 'AI', 'ai': 'AI',
            # Express variations
            'express': 'Express', 'express.js': 'Express', 'expressjs': 'Express',
            # Django variations
            'django': 'Django',
            # Flask variations
            'flask': 'Flask',
            # FastAPI variations
            'fastapi': 'FastAPI',
            # TensorFlow variations
            'tensorflow': 'TensorFlow', 'tf': 'TensorFlow',
            # PyTorch variations
            'pytorch': 'PyTorch', 'torch': 'PyTorch',
            # Pandas variations
            'pandas': 'Pandas',
            # NumPy variations
            'numpy': 'NumPy',
            # Scikit-learn variations
            'scikit-learn': 'Scikit-learn', 'sklearn': 'Scikit-learn', 'scikit learn': 'Scikit-learn',
            # HTML variations
            'html': 'HTML', 'html5': 'HTML',
            # CSS variations
            'css': 'CSS', 'css3': 'CSS',
            # Git variations
            'git': 'Git', 'github': 'Git',
            # REST API variations
            'rest': 'REST APIs', 'rest api': 'REST APIs', 'rest apis': 'REST APIs',
            'restful': 'REST APIs', 'restful api': 'REST APIs', 'api': 'REST APIs',
            # Next.js variations
            'next.js': 'Next.js', 'nextjs': 'Next.js', 'next': 'Next.js',
            # Tailwind variations
            'tailwind': 'Tailwind CSS', 'tailwind css': 'Tailwind CSS', 'tailwindcss': 'Tailwind CSS',
            # Bootstrap variations
            'bootstrap': 'Bootstrap',
            # Redis variations
            'redis': 'Redis',
            # Jest variations
            'jest': 'Jest',
            # Pytest variations
            'pytest': 'Pytest',
            # Spring Boot variations
            'spring boot': 'Spring Boot', 'springboot': 'Spring Boot',
            # Spring variations
            'spring': 'Spring',
            # Java variations
            'java': 'Java',
            # C++ variations
            'c++': 'C++', 'cpp': 'C++',
            # C# variations
            'c#': 'C#', 'csharp': 'C#',
            # Go variations
            'go': 'Go', 'golang': 'Go',
            # Rust variations
            'rust': 'Rust',
            # Ruby variations
            'ruby': 'Ruby',
            # PHP variations
            'php': 'PHP',
            # NestJS variations
            'nestjs': 'NestJS', 'nest.js': 'NestJS', 'nest': 'NestJS',
            # GraphQL variations
            'graphql': 'GraphQL',
            # Jupyter variations
            'jupyter': 'Jupyter', 'jupyter notebook': 'Jupyter', 'jupyter notebooks': 'Jupyter',
            # Vite variations
            'vite': 'Vite',
            # Webpack variations
            'webpack': 'Webpack',
            # Flutter variations
            'flutter': 'Flutter',
            # React Native variations
            'react native': 'React Native', 'react-native': 'React Native',
            # Kotlin variations
            'kotlin': 'Kotlin',
            # Swift variations
            'swift': 'Swift',
            # SASS variations
            'sass': 'SASS', 'scss': 'SASS',
            # SQL variations
            'sql': 'SQL',
            # Linux variations
            'linux': 'Linux',
            # Keras variations
            'keras': 'Keras',
        }

        self.skill_categories = {
            'frontend': ['React', 'Vue.js', 'Angular', 'Next.js', 'Svelte', 'HTML', 'CSS', 'JavaScript', 'TypeScript', 'jQuery', 'Bootstrap', 'Tailwind CSS', 'SASS'],
            'backend': ['Node.js', 'Express', 'Django', 'Flask', 'FastAPI', 'Spring Boot', 'Spring', 'NestJS', 'Laravel', 'Ruby on Rails'],
            'database': ['MongoDB', 'PostgreSQL', 'MySQL', 'Redis', 'Cassandra', 'DynamoDB', 'Oracle', 'SQL Server', 'Elasticsearch', 'SQL', 'Prisma'],
            'cloud': ['AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'Terraform', 'Jenkins'],
            'datascience': ['TensorFlow', 'PyTorch', 'Pandas', 'NumPy', 'Scikit-learn', 'Keras', 'Machine Learning', 'Jupyter'],
            'mobile': ['React Native', 'Flutter', 'Ionic', 'Swift', 'Kotlin'],
            'testing': ['Jest', 'Pytest', 'Mocha', 'Cypress', 'Selenium'],
            'languages': ['Python', 'Java', 'JavaScript', 'TypeScript', 'Go', 'Rust', 'C++', 'C#', 'Ruby', 'PHP'],
            'tools': ['Git', 'REST APIs', 'GraphQL', 'WebSocket', 'Webpack', 'Vite']
        }

    def match(self, resume_skills, github_skills):
        print("Matching skills...")
        print(f"   Resume skills: {len(resume_skills)}")
        print(f"   GitHub skills: {len(github_skills)}")

        normalized_resume_skills = self._normalize_skills(resume_skills)
        normalized_github_skills = self._normalize_skills(list(github_skills.keys()))

        # Create github skill map
        github_skill_map = {}
        for skill, data in github_skills.items():
            normalized = self._normalize_skill(skill)
            canonical = self._normalize_skill(self._get_canonical_skill(skill))
            github_skill_map[normalized] = {'original': skill, **data}
            if canonical != normalized:
                github_skill_map[canonical] = {'original': skill, **data}

        matched_skills = []
        missing_skills = []
        extra_skills = []

        # Match resume skills against GitHub
        for resume_skill in resume_skills:
            normalized_resume = self._normalize_skill(resume_skill)
            canonical_resume = self._normalize_skill(self._get_canonical_skill(resume_skill))

            match = self._find_match(normalized_resume, normalized_github_skills)
            
            if not match and canonical_resume != normalized_resume:
                match = self._find_match(canonical_resume, normalized_github_skills)

            if not match:
                if normalized_resume in github_skill_map:
                    match = normalized_resume
                elif canonical_resume in github_skill_map:
                    match = canonical_resume

            if match:
                github_data = github_skill_map.get(match) or github_skill_map.get(normalized_resume) or github_skill_map.get(canonical_resume) or {}
                matched_skills.append({
                    'skill': resume_skill,
                    'github_skill': github_data.get('original', match),
                    'confidence': github_data.get('confidence', 0),
                    'usage_frequency': github_data.get('usageFrequency', 0),
                    'repositories': github_data.get('repositories', []),
                    'evidence': github_data.get('evidence', []),
                    
                })
            else:
                fuzzy_match = self._find_fuzzy_match(normalized_resume, normalized_github_skills)
                if fuzzy_match:
                    github_data = github_skill_map.get(fuzzy_match, {})
                    matched_skills.append({
                        'skill': resume_skill,
                        'github_skill': github_data.get('original', fuzzy_match),
                        'confidence': (github_data.get('confidence', 0) * 0.8),
                        'usage_frequency': github_data.get('usageFrequency', 0),
                        'repositories': github_data.get('repositories', []),
                        'evidence': github_data.get('evidence', []),
                        
                    })
                else:
                    missing_skills.append({
                        'skill': resume_skill,
                        'reason': 'Not found in GitHub repositories',
                        'category': self._categorize_skill(resume_skill),
                        
                    })

        # Find extra skills in GitHub not in resume
        canonical_resume_skills = set()
        for resume_skill in resume_skills:
            canonical_resume_skills.add(self._normalize_skill(resume_skill))
            canonical_resume_skills.add(self._normalize_skill(self._get_canonical_skill(resume_skill)))

        for github_skill, github_data in github_skills.items():
            normalized_github = self._normalize_skill(github_skill)
            canonical_github = self._normalize_skill(self._get_canonical_skill(github_skill))

            is_in_resume = (
                normalized_github in canonical_resume_skills or
                canonical_github in canonical_resume_skills or
                self._find_match(normalized_github, normalized_resume_skills) or
                self._find_match(canonical_github, normalized_resume_skills)
            )

            if not is_in_resume:
                # Only include high confidence skills with real usage
                has_import_evidence = any(
                    'import' in e.lower() or 'found' in e.lower()
                    for e in github_data.get('evidence', [])
                )
                
                if github_data.get('confidence', 0) >= 90 and float(github_data.get('usageFrequency', 0)) >= 25 and has_import_evidence:
                    extra_skills.append({
                        'skill': github_skill,
                        'confidence': github_data.get('confidence', 0),
                        'usage_frequency': github_data.get('usageFrequency', 0),
                        'repositories': github_data.get('repositories', []),
                        'evidence': github_data.get('evidence', []),
                        'category': self._categorize_skill(github_skill),
                        'reason': self._explain_discovery(github_data),
                        'recommendation': f"Consider adding {github_skill} to your resume"
                    })

        # Calculate statistics
        total_resume_skills = len(resume_skills)
        matched_count = len(matched_skills)
        match_percentage = round((matched_count / total_resume_skills * 100), 2) if total_resume_skills > 0 else 0

        authenticity_score = self._calculate_authenticity_score(matched_skills, missing_skills, extra_skills)

        return {
            'matched_skills': matched_skills,
            'missing_skills': missing_skills,
            'extra_skills': extra_skills,
            'statistics': {
                'total_resume_skills': total_resume_skills,
                'total_github_skills': len(github_skills),
                'matched_count': matched_count,
                'missing_count': len(missing_skills),
                'extra_count': len(extra_skills),
                'match_percentage': match_percentage,
                'authenticity_score': authenticity_score
            }
        }

    def _normalize_skills(self, skills):
        return [self._normalize_skill(skill) for skill in skills]

    def _normalize_skill(self, skill):
        if not skill:
            return ''
        lower = skill.lower().strip()
        cleaned = re.sub(r'[^a-z0-9.\-\s+#]', '', lower)
        normalized = re.sub(r'\s+', ' ', cleaned).strip()
        return normalized

    def _get_canonical_skill(self, skill):
        if not skill:
            return ''
        normalized = self._normalize_skill(skill)
        return self.skill_canonical_map.get(normalized, skill)

    def _find_match(self, skill, skill_list):
        if skill in skill_list:
            return skill
        
        canonical = self._normalize_skill(self._get_canonical_skill(skill))
        if canonical in skill_list:
            return canonical
        
        for s in skill_list:
            if self._normalize_skill(self._get_canonical_skill(s)) == canonical:
                return s
        
        return None

    def _find_fuzzy_match(self, skill, skill_list):
        for s in skill_list:
            if skill in s or s in skill:
                return s
            
            skill_words = set(skill.split())
            s_words = set(s.split())
            if skill_words & s_words:
                return s
        
        return None

    def _categorize_skill(self, skill):
        normalized = self._normalize_skill(skill)
        canonical = self._get_canonical_skill(skill)
        
        for category, skills in self.skill_categories.items():
            if canonical in skills or any(self._normalize_skill(s) == normalized for s in skills):
                return category
        
        return 'other'

    def _explain_discovery(self, github_data):
        repos = github_data.get('repositories', [])[:3]
        if repos:
            return f"Found in: {', '.join(repos)}"
        return "Found in GitHub repositories"

    def _calculate_authenticity_score(self, matched_skills, missing_skills, extra_skills):
        if not matched_skills and not missing_skills:
            return 50

        total_claimed = len(matched_skills) + len(missing_skills)
        if total_claimed == 0:
            return 50

        # Base score from match percentage
        match_ratio = len(matched_skills) / total_claimed
        base_score = match_ratio * 100

        # Bonus for extra skills discovered
        extra_bonus = min(len(extra_skills) * 2, 10)

        total_score = base_score + extra_bonus
        return min(100, max(0, round(total_score, 2)))
