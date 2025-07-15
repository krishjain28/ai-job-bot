import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")

# Database
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/ai-job-bot")

# App Settings
RESUME_PATH = "resume.pdf"
MAX_JOBS_PER_RUN = 20
APPLICATION_DELAY = 30  # seconds between applications

# API Settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

import fitz  # PyMuPDF
import os
from typing import Optional

def extract_resume_text(file_path: str) -> Optional[str]:
    """Extract text content from PDF resume"""
    try:
        if not os.path.exists(file_path):
            print(f"Resume file not found: {file_path}")
            return None
            
        doc = fitz.open(file_path)
        text = "\n".join([page.get_text() for page in doc])
        doc.close()
        return text
    except Exception as e:
        print(f"Error parsing resume: {e}")
        return None

def extract_resume_sections(resume_text: str) -> dict:
    """Extract structured sections from resume text"""
    sections = {
        'skills': [],
        'experience': [],
        'education': [],
        'summary': ''
    }
    
    # Basic section extraction (can be enhanced with NLP)
    lines = resume_text.split('\n')
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Detect sections
        lower_line = line.lower()
        if any(keyword in lower_line for keyword in ['skills', 'technical skills', 'technologies']):
            current_section = 'skills'
        elif any(keyword in lower_line for keyword in ['experience', 'work history', 'employment']):
            current_section = 'experience'
        elif any(keyword in lower_line for keyword in ['education', 'academic', 'degree']):
            current_section = 'education'
        elif any(keyword in lower_line for keyword in ['summary', 'objective', 'profile']):
            current_section = 'summary'
        elif current_section and line:
            if current_section == 'summary':
                sections['summary'] += line + ' '
            else:
                sections[current_section].append(line)
    
    return sections

# Job scraper package

from playwright.sync_api import sync_playwright
import time
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

def scrape_remoteok(max_jobs: int = 20) -> List[Dict]:
    """Scrape remote jobs from RemoteOK"""
    jobs = []
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Set user agent to avoid detection
            page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            page.goto("https://remoteok.com/remote-dev-jobs")
            page.wait_for_selector(".job", timeout=10000)
            
            job_elements = page.query_selector_all(".job")[:max_jobs]
            
            for job in job_elements:
                try:
                    title_elem = job.query_selector("h2")
                    company_elem = job.query_selector(".company h3")
                    
                    if title_elem and company_elem:
                        title = title_elem.inner_text().strip()
                        company = company_elem.inner_text().strip()
                        link = "https://remoteok.com" + job.get_attribute("data-href")
                        
                        # Extract additional details
                        location = ""
                        salary = ""
                        tags = []
                        
                        location_elem = job.query_selector(".location")
                        if location_elem:
                            location = location_elem.inner_text().strip()
                            
                        salary_elem = job.query_selector(".salary")
                        if salary_elem:
                            salary = salary_elem.inner_text().strip()
                            
                        tag_elements = job.query_selector_all(".tag")
                        tags = [tag.inner_text().strip() for tag in tag_elements]
                        
                        jobs.append({
                            "title": title,
                            "company": company,
                            "link": link,
                            "location": location,
                            "salary": salary,
                            "tags": tags,
                            "source": "remoteok"
                        })
                        
                except Exception as e:
                    logger.warning(f"Error parsing job: {e}")
                    continue
                    
            browser.close()
            
    except Exception as e:
        logger.error(f"Error scraping RemoteOK: {e}")
        
    return jobs

from playwright.sync_api import sync_playwright
import time
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

def scrape_indeed(max_jobs: int = 20) -> List[Dict]:
    """Scrape remote jobs from Indeed"""
    jobs = []
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Set user agent
            page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            # Search for remote developer jobs
            page.goto("https://www.indeed.com/jobs?q=remote+developer&l=Remote")
            page.wait_for_selector('[data-testid="jobsearch-ResultsList"]', timeout=10000)
            
            job_cards = page.query_selector_all('[data-testid="jobsearch-ResultsList"] > div')[:max_jobs]
            
            for card in job_cards:
                try:
                    title_elem = card.query_selector('[data-testid="jobsearch-JobInfoHeader-title"]')
                    company_elem = card.query_selector('[data-testid="jobsearch-JobInfoHeader-companyName"]')
                    
                    if title_elem and company_elem:
                        title = title_elem.inner_text().strip()
                        company = company_elem.inner_text().strip()
                        
                        # Get job link
                        link_elem = card.query_selector('a[data-testid="jobsearch-JobInfoHeader-title"]')
                        link = "https://www.indeed.com" + link_elem.get_attribute("href") if link_elem else ""
                        
                        # Extract location
                        location = ""
                        location_elem = card.query_selector('[data-testid="jobsearch-JobInfoHeader-locationText"]')
                        if location_elem:
                            location = location_elem.inner_text().strip()
                        
                        jobs.append({
                            "title": title,
                            "company": company,
                            "link": link,
                            "location": location,
                            "salary": "",
                            "tags": [],
                            "source": "indeed"
                        })
                        
                except Exception as e:
                    logger.warning(f"Error parsing Indeed job: {e}")
                    continue
                    
            browser.close()
            
    except Exception as e:
        logger.error(f"Error scraping Indeed: {e}")
        
    return jobs

import openai
from typing import List, Dict
import logging
from config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

# Configure OpenAI
openai.api_key = OPENAI_API_KEY

def filter_jobs(jobs: List[Dict], resume_text: str) -> List[Dict]:
    """Filter jobs using GPT based on resume match"""
    filtered = []
    
    if not resume_text:
        logger.warning("No resume text provided for filtering")
        return jobs
    
    for job in jobs:
        try:
            # Create a comprehensive prompt for job matching
            prompt = f"""
            Resume Summary:
            {resume_text[:2000]}...

            Job Details:
            - Title: {job['title']}
            - Company: {job['company']}
            - Location: {job.get('location', 'Remote')}
            - Salary: {job.get('salary', 'Not specified')}
            - Tags: {', '.join(job.get('tags', []))}

            Based on the resume and job details above, rate this job match from 1-10 and provide a brief explanation.
            Consider:
            1. Skills alignment
            2. Experience level match
            3. Company size/type fit
            4. Location preferences

            Format your response as: "Score: X/10 - [brief explanation]"
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.3
            )
            
            answer = response["choices"][0]["message"]["content"].strip()
            
            # Extract score from response
            if "Score:" in answer:
                score_text = answer.split("Score:")[1].split("-")[0].strip()
                try:
                    score = int(score_text.split("/")[0])
                    if score >= 7:  # Only include high-matching jobs
                        job['gpt_score'] = score
                        job['gpt_reason'] = answer.split("-", 1)[1].strip() if "-" in answer else ""
                        filtered.append(job)
                except ValueError:
                    logger.warning(f"Could not parse GPT score: {score_text}")
                    
        except Exception as e:
            logger.error(f"Error filtering job {job.get('title', 'Unknown')}: {e}")
            continue
            
    # Sort by GPT score
    filtered.sort(key=lambda x: x.get('gpt_score', 0), reverse=True)
    
    return filtered

def generate_application_message(job: Dict, resume_text: str) -> str:
    """Generate a personalized application message using GPT"""
    try:
        prompt = f"""
        Resume:
        {resume_text[:1500]}...

        Job: {job['title']} at {job['company']}
        
        Generate a brief, professional application message (2-3 sentences) that:
        1. Shows enthusiasm for the role
        2. Mentions relevant experience from the resume
        3. Is personalized to the specific job/company
        4. Maintains a professional but friendly tone
        
        Keep it concise and natural.
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7
        )
        
        return response["choices"][0]["message"]["content"].strip()
        
    except Exception as e:
        logger.error(f"Error generating application message: {e}")
        return f"I'm excited to apply for the {job['title']} position at {job['company']}. I believe my experience aligns well with your requirements."

from playwright.sync_api import sync_playwright
import time
import random
import logging
from typing import Dict, Optional, List
from datetime import datetime
import os
from gpt_filter import generate_application_message
from job_scraper.linkedin import LinkedInScraper
from job_scraper.wellfound import WellfoundScraper

logger = logging.getLogger(__name__)

class JobApplicator:
    """Advanced job application automation system"""
    
    def __init__(self, resume_path: str, headless: bool = True):
        self.resume_path = resume_path
        self.headless = headless
        self.linkedin_scraper = LinkedInScraper(headless=headless)
        self.wellfound_scraper = WellfoundScraper(headless=headless)
        
        # Application settings
        self.delay_between_applications = 30  # seconds
        self.max_applications_per_run = 10
        self.require_cover_letter = False
        
        # Personal information (should be in config)
        self.personal_info = {
            'name': 'Your Name',
            'email': 'your.email@example.com',
            'phone': '+1234567890',
            'location': 'Remote',
            'linkedin': 'https://linkedin.com/in/yourprofile'
        }

    def apply_to_jobs(self, jobs: List[Dict], resume_text: str) -> List[Dict]:
        """Apply to a list of jobs"""
        results = []
        applications_sent = 0
        
        for i, job in enumerate(jobs):
            if applications_sent >= self.max_applications_per_run:
                logger.info(f"Reached maximum applications limit ({self.max_applications_per_run})")
                break
                
            try:
                logger.info(f"Applying to {job['title']} at {job['company']} ({i+1}/{len(jobs)})")
                
                # Generate personalized application message
                application_message = generate_application_message(job, resume_text)
                
                # Generate cover letter if required
                cover_letter = None
                if self.require_cover_letter or self._job_requires_cover_letter(job):
                    cover_letter = self._generate_cover_letter(job, resume_text)
                
                # Apply based on job source
                result = self._apply_to_job_by_source(job, application_message, cover_letter)
                
                # Add job info to result
                result['job_title'] = job['title']
                result['company'] = job['company']
                result['job_link'] = job['link']
                result['source'] = job.get('source', 'unknown')
                result['gpt_score'] = job.get('gpt_score', 0)
                
                results.append(result)
                
                if result['status'] == 'applied':
                    applications_sent += 1
                    
                # Delay between applications
                if i < len(jobs) - 1:
                    delay = random.uniform(self.delay_between_applications * 0.8, 
                                         self.delay_between_applications * 1.2)
                    logger.info(f"Waiting {delay:.1f} seconds before next application...")
                    time.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Error applying to job {job.get('title', 'Unknown')}: {e}")
                results.append({
                    'status': 'error',
                    'message': str(e),
                    'timestamp': datetime.utcnow().isoformat(),
                    'job_title': job.get('title', 'Unknown'),
                    'company': job.get('company', 'Unknown'),
                    'job_link': job.get('link', ''),
                    'source': job.get('source', 'unknown')
                })
                
        return results

    def _apply_to_job_by_source(self, job: Dict, application_message: str, cover_letter: str = None) -> Dict:
        """Apply to job based on its source"""
        source = job.get('source', '').lower()
        
        if 'linkedin' in source:
            return self.linkedin_scraper.apply_to_job(
                job['link'], 
                self.resume_path, 
                cover_letter
            )
        elif 'wellfound' in source:
            return self.wellfound_scraper.apply_to_job(
                job['link'], 
                self.resume_path, 
                cover_letter
            )
        elif 'remoteok' in source:
            return self._apply_to_remoteok_job(job, application_message, cover_letter)
        elif 'indeed' in source:
            return self._apply_to_indeed_job(job, application_message, cover_letter)
        else:
            return self._apply_to_generic_job(job, application_message, cover_letter)

    def _apply_to_remoteok_job(self, job: Dict, application_message: str, cover_letter: str = None) -> Dict:
        """Apply to RemoteOK job"""
        result = {
            'status': 'failed',
            'message': '',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                page = browser.new_page()
                
                # Set up anti-detection
                self._setup_page(page)
                
                # Navigate to job page
                page.goto(job['link'], wait_until="networkidle")
                time.sleep(random.uniform(2, 4))
                
                # Look for apply button
                apply_btn = page.query_selector('.apply-button, .apply-now, [data-action="apply"]')
                
                if apply_btn:
                    apply_btn.click()
                    time.sleep(random.uniform(2, 4))
                    
                    # Handle application form
                    result = self._handle_remoteok_form(page, application_message, cover_letter)
                else:
                    result['message'] = "Apply button not found on RemoteOK"
                    
                browser.close()
                
        except Exception as e:
            result['message'] = f"Error applying to RemoteOK job: {e}"
            logger.error(f"Error applying to RemoteOK job {job['link']}: {e}")
            
        return result

    def _apply_to_indeed_job(self, job: Dict, application_message: str, cover_letter: str = None) -> Dict:
        """Apply to Indeed job"""
        result = {
            'status': 'failed',
            'message': '',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                page = browser.new_page()
                
                # Set up anti-detection
                self._setup_page(page)
                
                # Navigate to job page
                page.goto(job['link'], wait_until="networkidle")
                time.sleep(random.uniform(2, 4))
                
                # Look for apply button
                apply_btn = page.query_selector('[data-testid="jobsearch-ApplyButton"]')
                
                if apply_btn:
                    apply_btn.click()
                    time.sleep(random.uniform(2, 4))
                    
                    # Handle application form
                    result = self._handle_indeed_form(page, application_message, cover_letter)
                else:
                    result['message'] = "Apply button not found on Indeed"
                    
                browser.close()
                
        except Exception as e:
            result['message'] = f"Error applying to Indeed job: {e}"
            logger.error(f"Error applying to Indeed job {job['link']}: {e}")
            
        return result

    def _apply_to_generic_job(self, job: Dict, application_message: str, cover_letter: str = None) -> Dict:
        """Apply to generic job (fallback)"""
        result = {
            'status': 'simulated',
            'message': application_message,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Simulated application to {job['title']} at {job['company']}")
        logger.info(f"Application message: {application_message}")
        
        if cover_letter:
            logger.info(f"Cover letter generated: {cover_letter[:100]}...")
            
        return result

    def _handle_remoteok_form(self, page, application_message: str, cover_letter: str = None) -> Dict:
        """Handle RemoteOK application form"""
        result = {
            'status': 'failed',
            'message': '',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        try:
            # Wait for form to load
            page.wait_for_selector('form', timeout=10000)
            
            # Fill in personal information
            self._fill_personal_info(page)
            
            # Upload resume
            self._upload_resume_generic(page)
            
            # Add cover letter if provided
            if cover_letter:
                self._add_cover_letter_generic(page, cover_letter)
                
            # Submit form
            submit_btn = page.query_selector('input[type="submit"], button[type="submit"]')
            if submit_btn:
                submit_btn.click()
                time.sleep(random.uniform(3, 5))
                
                # Check for success
                if "thank you" in page.content().lower() or "success" in page.content().lower():
                    result['status'] = 'applied'
                    result['message'] = 'Application submitted successfully'
                else:
                    result['message'] = 'Application submission may have failed'
            else:
                result['message'] = 'Submit button not found'
                
        except Exception as e:
            result['message'] = f"Error handling RemoteOK form: {e}"
            
        return result

    def _handle_indeed_form(self, page, application_message: str, cover_letter: str = None) -> Dict:
        """Handle Indeed application form"""
        result = {
            'status': 'failed',
            'message': '',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        try:
            # Indeed often redirects to external sites
            # This is a simplified implementation
            
            # Wait for form elements
            page.wait_for_selector('input, textarea', timeout=10000)
            
            # Fill in personal information
            self._fill_personal_info(page)
            
            # Upload resume
            self._upload_resume_generic(page)
            
            # Add cover letter if provided
            if cover_letter:
                self._add_cover_letter_generic(page, cover_letter)
                
            # Submit form
            submit_btn = page.query_selector('input[type="submit"], button[type="submit"]')
            if submit_btn:
                submit_btn.click()
                time.sleep(random.uniform(3, 5))
                
                result['status'] = 'applied'
                result['message'] = 'Application submitted (Indeed)'
            else:
                result['message'] = 'Submit button not found'
                
        except Exception as e:
            result['message'] = f"Error handling Indeed form: {e}"
            
        return result

    def _setup_page(self, page):
        """Set up page with anti-detection measures"""
        # Set user agent
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        page.set_extra_http_headers({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Set viewport
        page.set_viewport_size({"width": 1920, "height": 1080})

    def _fill_personal_info(self, page):
        """Fill in personal information on application forms"""
        try:
            # Common field mappings
            field_mappings = {
                'name': ['name', 'full_name', 'fullname', 'first_name', 'firstName'],
                'email': ['email', 'e-mail', 'email_address'],
                'phone': ['phone', 'telephone', 'mobile', 'cell'],
                'location': ['location', 'city', 'address', 'location_city']
            }
            
            for field_type, possible_names in field_mappings.items():
                value = self.personal_info.get(field_type, '')
                if not value:
                    continue
                    
                # Try different field selectors
                for name in possible_names:
                    selectors = [
                        f'input[name="{name}"]',
                        f'input[id="{name}"]',
                        f'input[placeholder*="{name}"]',
                        f'textarea[name="{name}"]'
                    ]
                    
                    for selector in selectors:
                        field = page.query_selector(selector)
                        if field:
                            field.fill(value)
                            time.sleep(random.uniform(0.5, 1))
                            break
                            
        except Exception as e:
            logger.warning(f"Error filling personal info: {e}")

    def _upload_resume_generic(self, page):
        """Upload resume to generic form"""
        try:
            if os.path.exists(self.resume_path):
                file_input = page.query_selector('input[type="file"]')
                if file_input:
                    file_input.set_input_files(self.resume_path)
                    time.sleep(random.uniform(1, 2))
                    logger.info("Resume uploaded successfully")
                    
        except Exception as e:
            logger.warning(f"Error uploading resume: {e}")

    def _add_cover_letter_generic(self, page, cover_letter: str):
        """Add cover letter to generic form"""
        try:
            # Try different selectors for cover letter field
            selectors = [
                'textarea[name="cover_letter"]',
                'textarea[name="coverLetter"]',
                'textarea[name="message"]',
                'textarea[name="description"]',
                'textarea[placeholder*="cover"]',
                'textarea[placeholder*="message"]'
            ]
            
            for selector in selectors:
                field = page.query_selector(selector)
                if field:
                    field.fill(cover_letter)
                    time.sleep(random.uniform(0.5, 1))
                    logger.info("Cover letter added successfully")
                    break
                    
        except Exception as e:
            logger.warning(f"Error adding cover letter: {e}")

    def _job_requires_cover_letter(self, job: Dict) -> bool:
        """Check if job requires a cover letter"""
        # Check job description for cover letter requirements
        description = job.get('description', '').lower()
        title = job.get('title', '').lower()
        
        cover_letter_indicators = [
            'cover letter', 'cover letter required', 'please include a cover letter',
            'motivation letter', 'personal statement', 'why you want to join'
        ]
        
        return any(indicator in description for indicator in cover_letter_indicators)

    def _generate_cover_letter(self, job: Dict, resume_text: str) -> str:
        """Generate a personalized cover letter using GPT"""
        try:
            from gpt_filter import openai
            
            prompt = f"""
            Job: {job['title']} at {job['company']}
            Job Description: {job.get('description', '')[:1000]}
            
            Resume Summary: {resume_text[:1000]}
            
            Generate a professional, personalized cover letter (2-3 paragraphs) that:
            1. Shows enthusiasm for the specific role and company
            2. Highlights relevant experience from the resume
            3. Explains why you're a good fit for this position
            4. Maintains a professional but friendly tone
            5. Is specific to this job/company
            
            Keep it concise (200-300 words) and natural.
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.7
            )
            
            return response["choices"][0]["message"]["content"].strip()
            
        except Exception as e:
            logger.error(f"Error generating cover letter: {e}")
            return f"I'm excited to apply for the {job['title']} position at {job['company']}. I believe my experience aligns well with your requirements and I'm eager to contribute to your team."

def auto_apply_stub(job: Dict, resume_text: str) -> Dict:
    """Legacy function for backward compatibility"""
    applicator = JobApplicator("resume.pdf")
    return applicator._apply_to_generic_job(job, "Generated application message", None)

def auto_apply_linkedin(job: Dict, resume_text: str) -> Dict:
    """Legacy function for backward compatibility"""
    applicator = JobApplicator("resume.pdf")
    return applicator.linkedin_scraper.apply_to_job(job['link'], "resume.pdf", None)

def auto_apply_indeed(job: Dict, resume_text: str) -> Dict:
    """Legacy function for backward compatibility"""
    applicator = JobApplicator("resume.pdf")
    return applicator._apply_to_indeed_job(job, "Generated application message", None) 