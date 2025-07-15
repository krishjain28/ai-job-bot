import requests
from bs4 import BeautifulSoup
import time
import random
import logging
from typing import List, Dict
from playwright.sync_api import sync_playwright

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
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            
            # Navigate to RemoteOK
            page.goto('https://remoteok.com/remote-python-jobs')
            page.wait_for_load_state('networkidle')
            
            # Add random delay
            time.sleep(random.uniform(2, 5))
            
            # Extract job listings
            job_elements = page.query_selector_all('.job')
            
            for job in job_elements[:max_jobs]:
                try:
                    title_elem = job.query_selector('.title')
                    if not title_elem:
                        continue
                        
                    title = title_elem.inner_text().strip()
                    
                    company_elem = job.query_selector('.company')
                    company = company_elem.inner_text().strip() if company_elem else "Unknown"
                    
                    link_elem = job.query_selector('a')
                    link = link_elem.get_attribute('href') if link_elem else ""
                    if link and not link.startswith('http'):
                        link = f"https://remoteok.com{link}"
                        
                    location_elem = job.query_selector('.location')
                    location = location_elem.inner_text().strip() if location_elem else "Remote"
                    
                    salary_elem = job.query_selector('.salary')
                    salary = salary_elem.inner_text().strip() if salary_elem else ""
                    
                    tag_elements = job.query_selector_all('.tag')
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
        