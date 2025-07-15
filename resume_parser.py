import fitz  # PyMuPDF
import os
import re
from typing import Optional, Dict, List, Tuple
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ResumeParser:
    """Advanced resume parser with skill extraction and keyword analysis"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.text = ""
        self.sections = {}
        
        # Common skill keywords
        self.tech_skills = [
            'python', 'javascript', 'java', 'react', 'node.js', 'sql', 'mongodb',
            'aws', 'docker', 'kubernetes', 'git', 'html', 'css', 'typescript',
            'angular', 'vue.js', 'django', 'flask', 'fastapi', 'postgresql',
            'redis', 'elasticsearch', 'kafka', 'rabbitmq', 'jenkins', 'ci/cd',
            'machine learning', 'ai', 'tensorflow', 'pytorch', 'scikit-learn',
            'data analysis', 'pandas', 'numpy', 'matplotlib', 'seaborn'
        ]
        
        self.soft_skills = [
            'leadership', 'communication', 'teamwork', 'problem solving',
            'project management', 'agile', 'scrum', 'collaboration',
            'time management', 'critical thinking', 'adaptability'
        ]

    def extract_text(self) -> Optional[str]:
        """Extract text content from PDF or text file"""
        try:
            if not os.path.exists(self.file_path):
                logger.error(f"Resume file not found: {self.file_path}")
                return None
                
            file_ext = os.path.splitext(self.file_path)[1].lower()
            
            if file_ext == '.pdf':
                return self._extract_pdf_text()
            elif file_ext in ['.txt', '.md']:
                return self._extract_text_file()
            else:
                # Try to open as text if PDF fails (for testing)
                try:
                    return self._extract_text_file()
                except Exception:
                    logger.error(f"Unsupported file format: {file_ext}")
                    return None
                
        except Exception as e:
            logger.error(f"Error extracting text from resume: {e}")
            return None

    def _extract_pdf_text(self) -> str:
        """Extract text from PDF file"""
        doc = fitz.open(self.file_path)
        text = ""
        
        for page in doc:
            text += page.get_text()
            
        doc.close()
        return text

    def _extract_text_file(self) -> str:
        """Extract text from plain text file"""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            return f.read()

    def parse_resume(self) -> Dict:
        """Parse resume and extract structured information"""
        self.text = self.extract_text()
        if not self.text:
            return {}
            
        # Extract sections
        self.sections = {
            'contact': self._extract_contact_info(),
            'summary': self._extract_summary(),
            'skills': self._extract_skills(),
            'experience': self._extract_experience(),
            'education': self._extract_education(),
            'keywords': self._extract_keywords()
        }
        
        return self.sections

    def _extract_contact_info(self) -> Dict:
        """Extract contact information"""
        contact = {
            'email': '',
            'phone': '',
            'location': '',
            'linkedin': ''
        }
        
        # Email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, self.text)
        if email_match:
            contact['email'] = email_match.group()
            
        # Phone pattern
        phone_pattern = r'(\+?1?[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
        phone_match = re.search(phone_pattern, self.text)
        if phone_match:
            contact['phone'] = phone_match.group()
            
        # LinkedIn pattern
        linkedin_pattern = r'linkedin\.com/in/[a-zA-Z0-9-]+'
        linkedin_match = re.search(linkedin_pattern, self.text)
        if linkedin_match:
            contact['linkedin'] = linkedin_match.group()
            
        return contact

    def _extract_summary(self) -> str:
        """Extract professional summary"""
        # Look for summary section
        summary_patterns = [
            r'(?:summary|profile|objective)[:\s]*([^•\n]+(?:\n[^•\n]+)*)',
            r'(?:about|overview)[:\s]*([^•\n]+(?:\n[^•\n]+)*)'
        ]
        
        for pattern in summary_patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
                
        # Fallback: first paragraph
        paragraphs = self.text.split('\n\n')
        if paragraphs:
            return paragraphs[0][:500]  # Limit to 500 chars
            
        return ""

    def _extract_skills(self) -> Dict[str, List[str]]:
        """Extract technical and soft skills"""
        skills = {
            'technical': [],
            'soft': [],
            'tools': [],
            'languages': []
        }
        
        # Find skills section
        skills_section = self._find_section('skills|technical skills|technologies')
        if skills_section:
            skills_text = skills_section.lower()
            
            # Extract technical skills
            for skill in self.tech_skills:
                if skill.lower() in skills_text:
                    skills['technical'].append(skill)
                    
            # Extract soft skills
            for skill in self.soft_skills:
                if skill.lower() in skills_text:
                    skills['soft'].append(skill)
                    
        # Also search in entire text for skills
        text_lower = self.text.lower()
        for skill in self.tech_skills:
            if skill.lower() in text_lower and skill not in skills['technical']:
                skills['technical'].append(skill)
                
        return skills

    def _extract_experience(self) -> List[Dict]:
        """Extract work experience"""
        experience = []
        
        # Find experience section
        exp_section = self._find_section('experience|work history|employment')
        if not exp_section:
            return experience
            
        # Split into individual experiences
        exp_blocks = re.split(r'\n(?=[A-Z][a-z]+ \d{4}|[A-Z][a-z]+ \d{4} -)', exp_section)
        
        for block in exp_blocks:
            if len(block.strip()) < 50:  # Skip short blocks
                continue
                
            exp = self._parse_experience_block(block)
            if exp:
                experience.append(exp)
                
        return experience

    def _parse_experience_block(self, block: str) -> Optional[Dict]:
        """Parse individual experience block"""
        try:
            # Extract job title and company
            title_company_pattern = r'^([^•\n]+?)(?:at|@|,)\s*([^•\n]+?)(?:\n|$)'
            match = re.search(title_company_pattern, block, re.IGNORECASE)
            
            if match:
                title = match.group(1).strip()
                company = match.group(2).strip()
                
                # Extract dates
                date_pattern = r'(\w+ \d{4})\s*(?:-|to)?\s*(\w+ \d{4}|Present|Current)?'
                date_match = re.search(date_pattern, block)
                
                start_date = ""
                end_date = ""
                if date_match:
                    start_date = date_match.group(1)
                    end_date = date_match.group(2) or "Present"
                    
                # Extract description
                description = block.split('\n', 2)[-1] if len(block.split('\n')) > 2 else ""
                
                return {
                    'title': title,
                    'company': company,
                    'start_date': start_date,
                    'end_date': end_date,
                    'description': description.strip()
                }
                
        except Exception as e:
            logger.warning(f"Error parsing experience block: {e}")
            
        return None

    def _extract_education(self) -> List[Dict]:
        """Extract education information"""
        education = []
        
        edu_section = self._find_section('education|academic|degree')
        if not edu_section:
            return education
            
        # Simple extraction - can be enhanced
        edu_blocks = edu_section.split('\n\n')
        
        for block in edu_blocks:
            if 'university' in block.lower() or 'college' in block.lower():
                education.append({
                    'institution': block.split('\n')[0],
                    'degree': block,
                    'year': ''
                })
                
        return education

    def _extract_keywords(self) -> List[str]:
        """Extract important keywords from resume"""
        keywords = []
        
        # Common job-related keywords
        job_keywords = [
            'developer', 'engineer', 'architect', 'manager', 'lead', 'senior',
            'full stack', 'frontend', 'backend', 'devops', 'data scientist',
            'machine learning', 'ai', 'automation', 'testing', 'deployment',
            'microservices', 'api', 'database', 'cloud', 'aws', 'azure'
        ]
        
        text_lower = self.text.lower()
        for keyword in job_keywords:
            if keyword.lower() in text_lower:
                keywords.append(keyword)
                
        return keywords

    def _find_section(self, section_name: str) -> str:
        """Find a specific section in the resume"""
        patterns = [
            rf'{section_name}[:\s]*\n([^A-Z\n]+(?:\n[^A-Z\n]+)*)',
            rf'{section_name}[:\s]*([^A-Z\n]+(?:\n[^A-Z\n]+)*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE | re.MULTILINE)
            if match and match.group(1):
                return match.group(1).strip()
                
        return ""

    def get_summary_text(self) -> str:
        """Get formatted summary text for job matching"""
        if not self.sections:
            self.parse_resume()
            
        summary_parts = []
        
        if self.sections.get('summary'):
            summary_parts.append(f"Summary: {self.sections['summary']}")
            
        if self.sections.get('skills', {}).get('technical'):
            skills = ', '.join(self.sections['skills']['technical'][:10])
            summary_parts.append(f"Technical Skills: {skills}")
            
        if self.sections.get('experience'):
            exp_summary = []
            for exp in self.sections['experience'][:3]:  # Last 3 experiences
                exp_summary.append(f"{exp['title']} at {exp['company']}")
            summary_parts.append(f"Recent Experience: {'; '.join(exp_summary)}")
            
        return '\n\n'.join(summary_parts)

def extract_resume_text(file_path: str) -> Optional[str]:
    """Legacy function for backward compatibility"""
    parser = ResumeParser(file_path)
    return parser.extract_text()

def extract_resume_sections(resume_text: str) -> dict:
    """Legacy function for backward compatibility"""
    # This would need to be enhanced to work with the new parser
    # For now, return basic structure
    return {
        'skills': [],
        'experience': [],
        'education': [],
        'summary': resume_text[:1000] if resume_text else ''
    } 