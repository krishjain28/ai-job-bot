import requests
from bs4 import BeautifulSoup
import time
import random
import logging
from typing import List, Dict
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

def scrape_indeed(max_jobs: int = 20) -> List[Dict]:
    """Scrape jobs from Indeed"""
    jobs = []
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Set user agent to avoid detection
            page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            
            # Navigate to Indeed
            page.goto('https://www.indeed.com/jobs?q=python+developer&l=remote')
            page.wait_for_load_state('networkidle')
            
            # Add random delay
            time.sleep(random.uniform(2, 5))
            
            # Extract job listings
            job_elements = page.query_selector_all('[data-jk]')
            
            for job in job_elements[:max_jobs]:
                try:
                    title_elem = job.query_selector('h2 a')
                    if not title_elem:
                        continue
                        
                    title = title_elem.inner_text().strip()
                    
                    company_elem = job.query_selector('.companyName')
                    company = company_elem.inner_text().strip() if company_elem else "Unknown"
                    
                    link = title_elem.get_attribute('href')
                    if link and not link.startswith('http'):
                        link = f"https://www.indeed.com{link}"
                        
                    location_elem = job.query_selector('.companyLocation')
                    location = location_elem.inner_text().strip() if location_elem else "Remote"
                    
                    salary_elem = job.query_selector('.salary-snippet')
                    salary = salary_elem.inner_text().strip() if salary_elem else ""
                    
                    # Extract job description snippet
                    desc_elem = job.query_selector('.job-snippet')
                    description = desc_elem.inner_text().strip() if desc_elem else ""
                    
                    jobs.append({
                        "title": title,
                        "company": company,
                        "link": link,
                        "location": location,
                        "salary": salary,
                        "description": description,
                        "source": "indeed"
                    })
                    
                except Exception as e:
                    logger.warning(f"Error parsing job: {e}")
                    continue
                    
            browser.close()
            
    except Exception as e:
        logger.error(f"Error scraping Indeed: {e}")
        
    return jobs
        