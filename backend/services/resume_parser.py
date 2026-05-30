import re
import os
from .pdf_link_extractor import extract_github_profile


class ResumeParser:
    def __init__(self):
        self.github_patterns = [
            r'github\.com/([a-zA-Z0-9-]+)',
            r'https?://(?:www\.)?github\.com/([a-zA-Z0-9-]+)',
        ]

        self.skill_keywords = [
            # Programming Languages
            'JavaScript', 'TypeScript', 'Python', 'Java', 'C++', 'C#', 'PHP', 'Ruby', 'Go', 'Rust',
            'Swift', 'Kotlin', 'Scala', 'R', 'MATLAB', 'Perl', 'Shell', 'Bash', 'PowerShell',
            # Frontend
            'React', 'Angular', 'Vue', 'Vue.js', 'Svelte', 'Next.js', 'Nuxt.js', 'jQuery',
            'HTML', 'HTML5', 'CSS', 'CSS3', 'SASS', 'SCSS', 'LESS', 'Tailwind', 'Bootstrap',
            'Material-UI', 'MUI', 'Chakra UI', 'Ant Design', 'Redux', 'MobX', 'Vuex', 'Pinia',
            'Webpack', 'Vite', 'Rollup', 'Parcel', 'Babel',
            # Backend
            'Node.js', 'Express', 'Express.js', 'Fastify', 'Koa', 'NestJS',
            'Django', 'Flask', 'FastAPI', 'Spring', 'Spring Boot', 'Hibernate',
            'ASP.NET', '.NET', 'Laravel', 'Symfony', 'Rails', 'Ruby on Rails',
            # Databases
            'MongoDB', 'MySQL', 'PostgreSQL', 'Redis', 'Cassandra', 'DynamoDB',
            'Oracle', 'SQL Server', 'SQLite', 'MariaDB', 'Elasticsearch', 'Neo4j',
            'Firebase', 'Firestore', 'Supabase',
            # Cloud & DevOps
            'AWS', 'Azure', 'GCP', 'Google Cloud', 'Docker', 'Kubernetes', 'K8s',
            'Jenkins', 'GitLab CI', 'GitHub Actions', 'CircleCI', 'Travis CI',
            'Terraform', 'Ansible', 'Puppet', 'Chef', 'Nginx', 'Apache',
            # Data Science & ML
            'TensorFlow', 'PyTorch', 'Keras', 'Scikit-learn', 'Pandas', 'NumPy',
            'Jupyter', 'Machine Learning', 'Deep Learning', 'NLP', 'Computer Vision',
            'OpenCV', 'NLTK', 'spaCy',
            # Mobile
            'React Native', 'Flutter', 'Ionic', 'Xamarin', 'Android', 'iOS',
            'SwiftUI', 'Jetpack Compose',
            # Testing
            'Jest', 'Mocha', 'Chai', 'Cypress', 'Selenium', 'Playwright', 'JUnit',
            'PyTest', 'TestNG', 'Jasmine', 'Karma',
            # Tools & Others
            'Git', 'GitHub', 'GitLab', 'Bitbucket', 'JIRA', 'Confluence',
            'Postman', 'Insomnia', 'Swagger', 'GraphQL', 'REST API', 'gRPC',
            'RabbitMQ', 'Kafka', 'WebSocket', 'Socket.io', 'Microservices',
            'Agile', 'Scrum', 'CI/CD', 'Linux', 'Unix', 'Windows Server'
        ]

        self.skill_normalization_map = {
            'nodejs': 'Node.js', 'node.js': 'Node.js', 'node': 'Node.js',
            'react': 'React', 'reactjs': 'React', 'react.js': 'React',
            'vue': 'Vue.js', 'vue.js': 'Vue.js', 'vuejs': 'Vue.js',
            'angular': 'Angular', 'angularjs': 'Angular', 'angular.js': 'Angular',
            'mongodb': 'MongoDB', 'mongo': 'MongoDB',
            'postgresql': 'PostgreSQL', 'postgres': 'PostgreSQL', 'psql': 'PostgreSQL',
            'mysql': 'MySQL',
            'javascript': 'JavaScript', 'js': 'JavaScript',
            'typescript': 'TypeScript', 'ts': 'TypeScript',
            'python': 'Python', 'python3': 'Python',
            'java': 'Java',
            'docker': 'Docker',
            'kubernetes': 'Kubernetes', 'k8s': 'Kubernetes',
            'aws': 'AWS', 'amazon web services': 'AWS',
            'azure': 'Azure', 'microsoft azure': 'Azure',
            'gcp': 'GCP', 'google cloud': 'GCP', 'google cloud platform': 'GCP',
            'tensorflow': 'TensorFlow', 'tf': 'TensorFlow',
            'pytorch': 'PyTorch', 'torch': 'PyTorch',
            'scikit-learn': 'Scikit-learn', 'sklearn': 'Scikit-learn',
            'pandas': 'Pandas',
            'numpy': 'NumPy',
            'html': 'HTML', 'html5': 'HTML',
            'css': 'CSS', 'css3': 'CSS',
            'git': 'Git',
            'express': 'Express', 'express.js': 'Express', 'expressjs': 'Express',
            'django': 'Django',
            'flask': 'Flask',
            'fastapi': 'FastAPI',
            'next.js': 'Next.js', 'nextjs': 'Next.js', 'next': 'Next.js',
            'tailwind': 'Tailwind CSS', 'tailwind css': 'Tailwind CSS', 'tailwindcss': 'Tailwind CSS',
            'rest api': 'REST APIs', 'rest apis': 'REST APIs', 'restful': 'REST APIs',
            'machine learning': 'Machine Learning', 'ml': 'Machine Learning',
            'graphql': 'GraphQL',
            'redis': 'Redis',
            'c++': 'C++', 'cpp': 'C++',
            'c#': 'C#', 'csharp': 'C#',
            'go': 'Go', 'golang': 'Go',
            'rust': 'Rust',
            'ruby': 'Ruby',
            'php': 'PHP',
            'spring boot': 'Spring Boot', 'springboot': 'Spring Boot',
            'spring': 'Spring',
            'nestjs': 'NestJS', 'nest.js': 'NestJS',
            'jest': 'Jest',
            'pytest': 'Pytest',
            'mocha': 'Mocha',
            'cypress': 'Cypress',
            'selenium': 'Selenium',
        }

    def parse(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.pdf':
            text = self._extract_pdf_text(file_path)
            # Use PyMuPDF-based extractor for better GitHub link extraction from PDFs
            github_url = self._extract_github_from_pdf(file_path)
        elif ext == '.docx':
            text = self._extract_docx_text(file_path)
            github_url = self._extract_github_url(text)
        else:
            raise Exception(f'Unsupported file format: {ext}')

        # Fallback to text extraction if PyMuPDF didn't find GitHub
        if not github_url:
            github_url = self._extract_github_url(text)

        name = self._extract_name(text)
        email = self._extract_email(text)
        phone = self._extract_phone(text)
        skills = self._extract_skills(text)

        return {
            'name': name,
            'email': email,
            'phone': phone,
            'github_url': github_url,
            'skills': skills,
            'raw_text': text
        }

    def _extract_github_from_pdf(self, file_path):
        """Extract GitHub username using PyMuPDF-based extractor"""
        try:
            result = extract_github_profile(file_path)
            if result.get('success') and result.get('username'):
                return result['username']
        except Exception as e:
            print(f"PDF link extractor failed: {e}")
        return None

    def _extract_pdf_text(self, file_path):
        text = ""
        
        # Try pdfplumber first (better for complex PDFs)
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            if text.strip():
                return text
        except Exception as e:
            print(f"pdfplumber failed: {e}")

        # Fallback to PyPDF2
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        except Exception as e:
            print(f"PyPDF2 failed: {e}")

        return text

    def _extract_docx_text(self, file_path):
        try:
            from docx import Document
            doc = Document(file_path)
            paragraphs = [para.text for para in doc.paragraphs]
            return '\n'.join(paragraphs)
        except Exception as e:
            raise Exception(f'Failed to parse DOCX: {str(e)}')

    def _extract_name(self, text):
        lines = text.strip().split('\n')
        for line in lines[:5]:
            cleaned = line.strip()
            if cleaned and len(cleaned) > 2 and len(cleaned) < 50:
                # Skip if it looks like contact info
                if '@' in cleaned or 'http' in cleaned.lower():
                    continue
                if re.match(r'^[\d\s\-\+\(\)]+$', cleaned):
                    continue
                # Check if it's potentially a name (contains letters)
                if re.match(r'^[A-Za-z\s\.\-\']+$', cleaned):
                    return cleaned
        return "Unknown"

    def _extract_email(self, text):
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        match = re.search(email_pattern, text)
        return match.group(0) if match else None

    def _extract_phone(self, text):
        phone_patterns = [
            r'\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'\+\d{1,3}[-.\s]?\d{10}',
            r'\d{10}'
        ]
        for pattern in phone_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return None

    def _extract_github_url(self, text):
        # Clean the text
        text = text.replace('\n', ' ').replace('\r', ' ')
        
        for pattern in self.github_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                username = match.group(1)
                # Filter out common false positives
                excluded = ['topics', 'explore', 'settings', 'notifications', 
                           'marketplace', 'pricing', 'about', 'login', 'join']
                if username.lower() not in excluded:
                    return username
        return None

    def _extract_skills(self, text):
        found_skills = set()
        text_lower = text.lower()

        # Direct keyword matching
        for skill in self.skill_keywords:
            pattern = r'\b' + re.escape(skill.lower()) + r'\b'
            if re.search(pattern, text_lower):
                normalized = self.skill_normalization_map.get(skill.lower(), skill)
                found_skills.add(normalized)

        # Also check for variations
        for variation, canonical in self.skill_normalization_map.items():
            pattern = r'\b' + re.escape(variation) + r'\b'
            if re.search(pattern, text_lower):
                found_skills.add(canonical)

        return list(found_skills)
