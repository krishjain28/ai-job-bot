import re
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

class FallbackJobEvaluator:
    """Fallback job evaluator using keyword matching when GPT API is unavailable"""
    
    def __init__(self):
        # Common tech skills and their variations
        self.tech_skills = {
            'python': ['python', 'django', 'flask', 'fastapi', 'pandas', 'numpy'],
            'javascript': ['javascript', 'js', 'node.js', 'react', 'vue', 'angular', 'typescript'],
            'java': ['java', 'spring', 'maven', 'gradle'],
            'c++': ['c++', 'cpp', 'c plus plus'],
            'c#': ['c#', 'csharp', '.net', 'asp.net'],
            'go': ['go', 'golang'],
            'rust': ['rust'],
            'php': ['php', 'laravel', 'wordpress'],
            'ruby': ['ruby', 'rails'],
            'swift': ['swift', 'ios'],
            'kotlin': ['kotlin', 'android'],
            'scala': ['scala'],
            'r': ['r', 'rstudio'],
            'matlab': ['matlab'],
            'sql': ['sql', 'mysql', 'postgresql', 'mongodb', 'redis'],
            'aws': ['aws', 'amazon web services', 'ec2', 's3', 'lambda'],
            'azure': ['azure', 'microsoft azure'],
            'gcp': ['gcp', 'google cloud', 'google cloud platform'],
            'docker': ['docker', 'containerization'],
            'kubernetes': ['kubernetes', 'k8s'],
            'terraform': ['terraform'],
            'ansible': ['ansible'],
            'jenkins': ['jenkins', 'ci/cd'],
            'git': ['git', 'github', 'gitlab'],
            'linux': ['linux', 'unix', 'ubuntu', 'centos'],
            'machine_learning': ['machine learning', 'ml', 'ai', 'artificial intelligence', 'deep learning', 'neural networks'],
            'data_science': ['data science', 'data analysis', 'statistics', 'analytics'],
            'devops': ['devops', 'site reliability', 'sre'],
            'frontend': ['frontend', 'front-end', 'ui', 'ux', 'user interface'],
            'backend': ['backend', 'back-end', 'api', 'rest', 'graphql'],
            'fullstack': ['fullstack', 'full-stack', 'full stack'],
            'mobile': ['mobile', 'ios', 'android', 'react native', 'flutter'],
            'cloud': ['cloud', 'aws', 'azure', 'gcp', 'serverless'],
            'security': ['security', 'cybersecurity', 'penetration testing', 'ethical hacking'],
            'blockchain': ['blockchain', 'ethereum', 'bitcoin', 'web3', 'defi'],
            'game_dev': ['game development', 'unity', 'unreal engine', 'gaming'],
            'embedded': ['embedded', 'iot', 'internet of things', 'arduino', 'raspberry pi'],
        }
        
        # Experience level keywords
        self.experience_levels = {
            'junior': ['junior', 'entry', 'entry-level', 'graduate', 'intern', '0-2', '1-2'],
            'mid': ['mid', 'mid-level', 'intermediate', '3-5', '4-6'],
            'senior': ['senior', 'lead', 'principal', '5+', '6+', '7+', '8+'],
            'staff': ['staff', 'architect', '10+', '12+']
        }
        
        # Company size indicators
        self.company_sizes = {
            'startup': ['startup', 'start-up', 'early stage', 'seed', 'series a', 'series b'],
            'scaleup': ['scaleup', 'scale-up', 'growth', 'series c', 'series d'],
            'enterprise': ['enterprise', 'fortune 500', 'large', 'established', 'corporate'],
            'agency': ['agency', 'consulting', 'consultant', 'freelance']
        }
    
    def evaluate_job(self, job: Dict, resume_text: str) -> Tuple[int, str]:
        """
        Evaluate job match using keyword matching
        Returns: (score, reason)
        """
        job_text = self._extract_job_text(job)
        resume_lower = resume_text.lower()
        job_lower = job_text.lower()
        
        # Calculate skill match
        skill_score = self._calculate_skill_match(resume_lower, job_lower)
        
        # Calculate experience level match
        experience_score = self._calculate_experience_match(resume_lower, job_lower)
        
        # Calculate company fit
        company_score = self._calculate_company_fit(resume_lower, job_lower)
        
        # Calculate overall score (1-10)
        total_score = min(10, max(1, int((skill_score + experience_score + company_score) / 3)))
        
        # Generate reason
        reason = self._generate_reason(skill_score, experience_score, company_score, job)
        
        return total_score, reason
    
    def _extract_job_text(self, job: Dict) -> str:
        """Extract all relevant text from job posting"""
        text_parts = [
            job.get('title', ''),
            job.get('company', ''),
            job.get('description', ''),
            ' '.join(job.get('tags', [])),
            job.get('requirements', ''),
            job.get('responsibilities', '')
        ]
        return ' '.join(filter(None, text_parts))
    
    def _calculate_skill_match(self, resume_text: str, job_text: str) -> float:
        """Calculate skill match score (0-10)"""
        resume_skills = set()
        job_skills = set()
        
        # Extract skills from resume
        for skill_category, variations in self.tech_skills.items():
            for variation in variations:
                if variation in resume_text:
                    resume_skills.add(skill_category)
                    break
        
        # Extract skills from job
        for skill_category, variations in self.tech_skills.items():
            for variation in variations:
                if variation in job_text:
                    job_skills.add(skill_category)
                    break
        
        if not job_skills:
            return 5.0  # Neutral if no specific skills mentioned
        
        # Calculate overlap
        overlap = len(resume_skills.intersection(job_skills))
        total_required = len(job_skills)
        
        if total_required == 0:
            return 5.0
        
        match_percentage = overlap / total_required
        return min(10.0, match_percentage * 10)
    
    def _calculate_experience_match(self, resume_text: str, job_text: str) -> float:
        """Calculate experience level match (0-10)"""
        # Simple heuristic: count years mentioned
        resume_years = self._extract_years(resume_text)
        job_years = self._extract_years(job_text)
        
        if not job_years:
            return 5.0  # Neutral if no experience requirement
        
        # Check if resume has enough experience
        if resume_years and max(resume_years) >= min(job_years):
            return 8.0
        elif resume_years and max(resume_years) >= min(job_years) * 0.7:
            return 6.0
        else:
            return 3.0
    
    def _extract_years(self, text: str) -> List[int]:
        """Extract years of experience from text"""
        # Look for patterns like "5+ years", "3-5 years", etc.
        patterns = [
            r'(\d+)\+?\s*years?',
            r'(\d+)-(\d+)\s*years?',
            r'(\d+)\s*to\s*(\d+)\s*years?'
        ]
        
        years = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    years.extend([int(x) for x in match])
                else:
                    years.append(int(match))
        
        return years
    
    def _calculate_company_fit(self, resume_text: str, job_text: str) -> float:
        """Calculate company fit score (0-10)"""
        # This is a simplified version - in practice you might want more sophisticated logic
        return 6.0  # Neutral score for company fit
    
    def _generate_reason(self, skill_score: float, experience_score: float, 
                        company_score: float, job: Dict) -> str:
        """Generate a reason for the evaluation"""
        avg_score = (skill_score + experience_score + company_score) / 3
        
        if avg_score >= 8:
            return f"Strong match for {job.get('title', 'position')} - skills and experience align well"
        elif avg_score >= 6:
            return f"Good match for {job.get('title', 'position')} - some skills overlap"
        elif avg_score >= 4:
            return f"Moderate match for {job.get('title', 'position')} - limited skill overlap"
        else:
            return f"Weak match for {job.get('title', 'position')} - skills don't align well"

# Global fallback evaluator instance
_fallback_evaluator = None

def get_fallback_evaluator() -> FallbackJobEvaluator:
    """Get global fallback evaluator instance"""
    global _fallback_evaluator
    if _fallback_evaluator is None:
        _fallback_evaluator = FallbackJobEvaluator()
    return _fallback_evaluator 