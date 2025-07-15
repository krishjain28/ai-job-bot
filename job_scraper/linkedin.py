from playwright.sync_api import sync_playwright
import time
import random
import logging
from typing import List, Dict, Optional
from datetime import datetime
import os
from utils.selector_registry import get_selector_registry
from utils.anti_bot import get_anti_bot_manager
from utils.network_resilience import get_network_resilience_manager

logger = logging.getLogger(__name__)

class LinkedInScraper:
    """LinkedIn job scraper with anti-detection measures and resilience features"""
    
    def __init__(self, headless: bool = True, use_proxy: bool = False):
        self.headless = headless
        self.use_proxy = use_proxy
        self.selector_registry = get_selector_registry()
        self.anti_bot_manager = get_anti_bot_manager()
        self.network_manager = get_network_resilience_manager()
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]

    def scrape_jobs(self, keywords: List[str] = None, location: str = "Remote", max_jobs: int = 20) -> List[Dict]:
        """Scrape jobs from LinkedIn"""
        jobs = []
        
        if not keywords:
            keywords = ["software engineer", "developer", "full stack", "backend", "frontend"]
            
        try:
            with sync_playwright() as p:
                browser = self._launch_browser(p)
                page = browser.new_page()
                
                # Set up anti-detection measures
                self._setup_page(page)
                
                for keyword in keywords[:3]:  # Limit to 3 keywords to avoid rate limiting
                    try:
                        keyword_jobs = self._scrape_keyword_jobs(page, keyword, location, max_jobs // len(keywords))
                        jobs.extend(keyword_jobs)
                        
                        # Random delay between keywords
                        time.sleep(random.uniform(2, 5))
                        
                    except Exception as e:
                        logger.error(f"Error scraping keyword '{keyword}': {e}")
                        continue
                        
                browser.close()
                
        except Exception as e:
            logger.error(f"Error in LinkedIn scraping: {e}")
            
        return jobs[:max_jobs]

    def _launch_browser(self, playwright):
        """Launch browser with anti-detection settings"""
        browser_args = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding'
        ]
        
        if self.use_proxy:
            # Add proxy configuration here if needed
            pass
            
        return playwright.chromium.launch(
            headless=self.headless,
            args=browser_args
        )

    def _setup_page(self, page):
        """Set up page with anti-detection measures"""
        # Set user agent
        user_agent = random.choice(self.user_agents)
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
        
        # Add random mouse movements and scrolling
        page.add_init_script("""
            // Override webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)

    def _scrape_keyword_jobs(self, page, keyword: str, location: str, max_jobs: int) -> List[Dict]:
        """Scrape jobs for a specific keyword"""
        jobs = []
        
        try:
            # Construct LinkedIn job search URL
            search_url = f"https://www.linkedin.com/jobs/search/?keywords={keyword.replace(' ', '%20')}&location={location.replace(' ', '%20')}&f_WT=2"  # f_WT=2 for remote jobs
            
            logger.info(f"Searching LinkedIn for: {keyword} in {location}")
            
            # Navigate to search page
            page.goto(search_url, wait_until="networkidle")
            time.sleep(random.uniform(2, 4))
            
            # Wait for job listings to load using fallback selectors
            self._wait_for_job_cards(page)
            
            # Scroll to load more jobs
            self._scroll_page(page)
            
            # Get job cards using fallback selectors
            job_cards = self._get_job_cards_with_fallbacks(page)[:max_jobs]
            
            for card in job_cards:
                try:
                    job = self._extract_job_from_card(card, page)
                    if job:
                        job['source'] = 'linkedin'
                        job['search_keyword'] = keyword
                        jobs.append(job)
                        
                except Exception as e:
                    logger.warning(f"Error extracting job from card: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error scraping keyword jobs: {e}")
            
        return jobs

    def _extract_job_from_card(self, card, page) -> Optional[Dict]:
        """Extract job information from a job card using selector fallbacks"""
        try:
            # Extract job title using fallback selectors
            title = self._extract_with_fallbacks(card, "job_title")
            
            # Extract company name using fallback selectors
            company = self._extract_with_fallbacks(card, "company_name")
            
            # Extract location using fallback selectors
            location = self._extract_with_fallbacks(card, "location")
            
            # Extract job link using fallback selectors
            link = self._extract_with_fallbacks(card, "job_link", is_link=True)
            if link and not link.startswith('http'):
                link = f"https://www.linkedin.com{link}"
                
            # Extract additional details
            details = self._extract_job_details(card)
            
            if title and company:
                return {
                    'title': title,
                    'company': company,
                    'location': location,
                    'link': link,
                    'salary': details.get('salary', ''),
                    'posted_date': details.get('posted_date', ''),
                    'job_type': details.get('job_type', ''),
                    'experience_level': details.get('experience_level', ''),
                    'tags': details.get('tags', []),
                    'description': details.get('description', ''),
                    'scraped_at': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.warning(f"Error extracting job from card: {e}")
            
        return None
    
    def _extract_with_fallbacks(self, card, selector_type: str, is_link: bool = False) -> str:
        """Extract text or link using selector fallbacks"""
        selectors = self.selector_registry.get_all_selectors("linkedin", selector_type)
        
        for selector in selectors:
            try:
                element = card.query_selector(selector)
                if element:
                    if is_link:
                        return element.get_attribute("href") or ""
                    else:
                        return element.inner_text().strip()
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        return ""
    
    def _wait_for_job_cards(self, page):
        """Wait for job cards to load using fallback selectors"""
        selectors = self.selector_registry.get_all_selectors("linkedin", "job_cards")
        
        for selector in selectors:
            try:
                page.wait_for_selector(selector, timeout=10000)
                logger.debug(f"Found job cards with selector: {selector}")
                return
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        logger.warning("No job cards found with any selector")
    
    def _get_job_cards_with_fallbacks(self, page):
        """Get job cards using fallback selectors"""
        selectors = self.selector_registry.get_all_selectors("linkedin", "job_cards")
        
        for selector in selectors:
            try:
                cards = page.query_selector_all(selector)
                if cards:
                    logger.debug(f"Found {len(cards)} job cards with selector: {selector}")
                    return cards
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        logger.warning("No job cards found with any selector")
        return []

    def _extract_job_details(self, card) -> Dict:
        """Extract additional job details from card"""
        details = {
            'salary': '',
            'posted_date': '',
            'job_type': '',
            'experience_level': '',
            'tags': [],
            'description': ''
        }
        
        try:
            # Extract salary if available
            salary_elem = card.query_selector('[data-testid="job-card-container__salary"]')
            if salary_elem:
                details['salary'] = salary_elem.inner_text().strip()
                
            # Extract posted date
            date_elem = card.query_selector('[data-testid="job-card-container__posted-date"]')
            if date_elem:
                details['posted_date'] = date_elem.inner_text().strip()
                
            # Extract job type (full-time, part-time, etc.)
            type_elem = card.query_selector('[data-testid="job-card-container__job-type"]')
            if type_elem:
                details['job_type'] = type_elem.inner_text().strip()
                
            # Extract experience level
            level_elem = card.query_selector('[data-testid="job-card-container__experience-level"]')
            if level_elem:
                details['experience_level'] = level_elem.inner_text().strip()
                
            # Extract tags/skills
            tag_elems = card.query_selector_all('[data-testid="job-card-container__skill"]')
            details['tags'] = [tag.inner_text().strip() for tag in tag_elems if tag.inner_text().strip()]
            
        except Exception as e:
            logger.warning(f"Error extracting job details: {e}")
            
        return details

    def _scroll_page(self, page):
        """Scroll page to load more content"""
        try:
            # Scroll down multiple times to load more jobs
            for i in range(3):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(random.uniform(1, 2))
                
                # Wait for new content to load
                page.wait_for_timeout(2000)
                
        except Exception as e:
            logger.warning(f"Error scrolling page: {e}")

    def apply_to_job(self, job_url: str, resume_path: str, cover_letter: str = None) -> Dict:
        """Apply to a specific LinkedIn job"""
        result = {
            'status': 'failed',
            'message': '',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        try:
            with sync_playwright() as p:
                browser = self._launch_browser(p)
                page = browser.new_page()
                self._setup_page(page)
                
                # Navigate to job page
                page.goto(job_url, wait_until="networkidle")
                time.sleep(random.uniform(2, 4))
                
                # Look for Easy Apply button
                easy_apply_btn = page.query_selector('[data-testid="job-details-easy-apply-button"]')
                
                if easy_apply_btn:
                    # Click Easy Apply
                    easy_apply_btn.click()
                    time.sleep(random.uniform(2, 4))
                    
                    # Handle application form
                    result = self._handle_application_form(page, resume_path, cover_letter)
                else:
                    result['message'] = "Easy Apply not available for this job"
                    
                browser.close()
                
        except Exception as e:
            result['message'] = f"Error applying to job: {e}"
            logger.error(f"Error applying to job {job_url}: {e}")
            
        return result

    def _handle_application_form(self, page, resume_path: str, cover_letter: str = None) -> Dict:
        """Handle LinkedIn application form"""
        result = {
            'status': 'failed',
            'message': '',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        try:
            # Wait for form to load
            page.wait_for_selector('[data-testid="job-details-easy-apply-form"]', timeout=10000)
            
            # Fill in form fields
            self._fill_application_fields(page)
            
            # Upload resume if needed
            self._upload_resume(page, resume_path)
            
            # Add cover letter if provided
            if cover_letter:
                self._add_cover_letter(page, cover_letter)
                
            # Submit application
            submit_btn = page.query_selector('[data-testid="job-details-easy-apply-submit-button"]')
            if submit_btn:
                submit_btn.click()
                time.sleep(random.uniform(3, 5))
                
                # Check if application was successful
                success_elem = page.query_selector('[data-testid="application-success"]')
                if success_elem:
                    result['status'] = 'applied'
                    result['message'] = 'Application submitted successfully'
                else:
                    result['message'] = 'Application submission failed'
            else:
                result['message'] = 'Submit button not found'
                
        except Exception as e:
            result['message'] = f"Error handling application form: {e}"
            
        return result

    def _fill_application_fields(self, page):
        """Fill in application form fields"""
        try:
            # Fill in common fields like name, email, phone
            # This is a simplified version - actual implementation would be more complex
            
            # Example: Fill name field
            name_field = page.query_selector('input[name="name"]')
            if name_field:
                name_field.fill("Your Name")
                
            # Example: Fill email field
            email_field = page.query_selector('input[name="email"]')
            if email_field:
                email_field.fill("your.email@example.com")
                
        except Exception as e:
            logger.warning(f"Error filling application fields: {e}")

    def _upload_resume(self, page, resume_path: str):
        """Upload resume to application form"""
        try:
            # Look for file upload input
            file_input = page.query_selector('input[type="file"]')
            if file_input and os.path.exists(resume_path):
                file_input.set_input_files(resume_path)
                time.sleep(random.uniform(1, 2))
                
        except Exception as e:
            logger.warning(f"Error uploading resume: {e}")

    def _add_cover_letter(self, page, cover_letter: str):
        """Add cover letter to application"""
        try:
            # Look for cover letter textarea
            cover_letter_field = page.query_selector('textarea[name="coverLetter"]')
            if cover_letter_field:
                cover_letter_field.fill(cover_letter)
                
        except Exception as e:
            logger.warning(f"Error adding cover letter: {e}")

def scrape_linkedin(max_jobs: int = 20) -> List[Dict]:
    """Convenience function for scraping LinkedIn jobs"""
    scraper = LinkedInScraper()
    return scraper.scrape_jobs(max_jobs=max_jobs) 