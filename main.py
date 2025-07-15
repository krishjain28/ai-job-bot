#!/usr/bin/env python3
"""
AI Job Application Automation - Main Orchestrator
Enhanced with comprehensive resilience, monitoring, and error handling
"""

import asyncio
import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Import all resilience and monitoring systems
from utils.error_handler import get_error_handler, reset_error_handler
from utils.circuit_breaker import get_circuit_breaker_manager, reset_circuit_breaker_manager
from utils.data_consistency import get_data_consistency_manager, reset_data_consistency_manager
from utils.security import get_security_manager, reset_security_manager
from utils.monitoring import get_monitoring_manager, reset_monitoring_manager
from utils.db_optimizer import get_db_optimizer, reset_db_optimizer
from utils.gpt_manager import get_gpt_manager, reset_gpt_manager
from utils.cache import get_cache_manager, reset_cache_manager
from utils.api_resilience import get_api_resilience_manager, reset_api_resilience_manager
from utils.selector_registry import get_selector_registry, reset_selector_registry
from utils.captcha_handler import get_captcha_handler, reset_captcha_handler
from utils.sheets_logger import get_sheets_logger, reset_sheets_logger
from utils.browser_manager import get_browser_manager, BrowserConfig, reset_browser_manager
from utils.critical_path_logger import get_critical_path_logger, reset_critical_path_logger, PipelineStage, log_pipeline_stage

# Import core modules
from resume_parser import ResumeParser
from scrapers.linkedin_scraper import LinkedInScraper
from scrapers.wellfound_scraper import WellfoundScraper
from gpt_filter import GPTFilter
from apply import JobApplicator
from logger import SheetsLogger
import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_job_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AIJobBot:
    """Enhanced AI Job Application Bot with comprehensive resilience"""
    
    def __init__(self):
        self.resume_parser = ResumeParser()
        self.gpt_filter = GPTFilter()
        self.applicator = JobApplicator()
        
        # Initialize all resilience managers
        self.error_handler = get_error_handler()
        self.circuit_breaker_manager = get_circuit_breaker_manager()
        self.data_consistency_manager = get_data_consistency_manager()
        self.security_manager = get_security_manager()
        self.monitoring_manager = get_monitoring_manager()
        self.db_optimizer = get_db_optimizer()
        self.gpt_manager = get_gpt_manager()
        self.cache_manager = get_cache_manager()
        self.api_resilience_manager = get_api_resilience_manager()
        self.selector_registry = get_selector_registry()
        self.captcha_handler = get_captcha_handler()
        self.sheets_logger = get_sheets_logger()
        self.critical_path_logger = get_critical_path_logger()
        
        # Initialize browser manager with configuration
        browser_config = BrowserConfig(
            headless=config.HEADLESS_MODE,
            max_pages_per_context=5,
            max_contexts=3,
            memory_limit_mb=1024,
            cpu_limit_percent=80,
            restart_interval_minutes=30,
            max_operations_before_restart=100
        )
        self.browser_manager = get_browser_manager(browser_config)
        
        # Initialize scrapers with enhanced resilience
        self.linkedin_scraper = LinkedInScraper()
        self.wellfound_scraper = WellfoundScraper()
        
        # Pipeline metrics
        self.pipeline_metrics = {
            'total_runs': 0,
            'successful_runs': 0,
            'failed_runs': 0,
            'total_jobs_processed': 0,
            'total_applications_sent': 0,
            'last_run_time': None,
            'average_run_duration': 0.0
        }
    
    async def initialize(self):
        """Initialize all systems with error handling"""
        try:
            logger.info("🚀 Initializing AI Job Bot with enhanced resilience...")
            
            # Initialize browser manager
            await self.browser_manager.initialize()
            
            # Register selectors for all sites
            self._register_selectors()
            
            # Set up CAPTCHA handler callbacks
            self.captcha_handler.set_manual_fallback_callback(self._manual_captcha_fallback)
            
            # Set up browser manager callbacks
            self.browser_manager.set_callbacks(
                on_restart=self._on_browser_restart,
                on_error=self._on_browser_error
            )
            
            # Set up critical path logger callbacks
            self.critical_path_logger.add_alert_callback(self._on_critical_alert)
            
            logger.info("✅ AI Job Bot initialized successfully")
            
        except Exception as e:
            logger.critical(f"❌ Failed to initialize AI Job Bot: {e}")
            await self.error_handler.handle_error(e, {'operation': 'initialization'})
            raise
    
    def _register_selectors(self):
        """Register selectors for all job sites with fallbacks"""
        # LinkedIn selectors with fallbacks
        linkedin_selectors = {
            'job_cards': [
                '.job-search-card',
                '.job-card-container',
                '[data-job-id]',
                '.job-result-card'
            ],
            'job_title': [
                '.job-search-card__title',
                '.job-card__title',
                'h3 a',
                '.job-title'
            ],
            'company_name': [
                '.job-search-card__subtitle',
                '.job-card__company',
                '.company-name',
                '.employer-name'
            ],
            'job_link': [
                '.job-search-card__title a',
                '.job-card__title a',
                'h3 a',
                '.job-title a'
            ]
        }
        
        # Wellfound selectors with fallbacks
        wellfound_selectors = {
            'job_cards': [
                '.job-card',
                '.job-listing',
                '[data-testid="job-card"]',
                '.job-item'
            ],
            'job_title': [
                '.job-card__title',
                '.job-title',
                'h3',
                '.title'
            ],
            'company_name': [
                '.job-card__company',
                '.company-name',
                '.employer',
                '.company'
            ],
            'job_link': [
                '.job-card__title a',
                '.job-title a',
                'h3 a',
                'a[href*="/jobs/"]'
            ]
        }
        
        self.selector_registry.register_selectors('linkedin', linkedin_selectors)
        self.selector_registry.register_selectors('wellfound', wellfound_selectors)
        
        logger.info("✅ Selectors registered with fallbacks")
    
    async def _manual_captcha_fallback(self, challenge, page):
        """Manual CAPTCHA fallback handler"""
        logger.critical(f"MANUAL CAPTCHA REQUIRED: {challenge.site} - {challenge.type.value}")
        
        # Send email alert
        await self.monitoring_manager.send_alert(
            'manual_captcha',
            f"Manual CAPTCHA solving required for {challenge.site}",
            severity='critical'
        )
        
        # For now, return False to skip this job
        # In production, you might want to pause and wait for manual intervention
        return False
    
    async def _on_browser_restart(self, metrics):
        """Browser restart callback"""
        logger.info(f"Browser restarted - Metrics: {metrics}")
        await self.monitoring_manager.send_alert(
            'browser_restart',
            f"Browser restarted after {metrics.uptime_seconds:.1f}s uptime",
            severity='warning'
        )
    
    async def _on_browser_error(self, error, metrics):
        """Browser error callback"""
        logger.error(f"Browser error: {error}")
        await self.monitoring_manager.send_alert(
            'browser_error',
            f"Browser error: {str(error)}",
            severity='error'
        )
    
    async def _on_critical_alert(self, alert_data):
        """Critical alert callback"""
        logger.critical(f"Critical alert: {alert_data}")
        await self.monitoring_manager.send_alert(
            'pipeline_critical',
            f"Pipeline stage failure: {alert_data['stage']}",
            severity='critical'
        )
    
    @log_pipeline_stage(PipelineStage.RESUME_PARSING)
    async def parse_resume(self, resume_path: str) -> Dict[str, Any]:
        """Parse resume with enhanced error handling"""
        try:
            resume_data = await self.resume_parser.parse_resume(resume_path)
            logger.info(f"✅ Resume parsed successfully: {len(resume_data.get('skills', []))} skills found")
            return resume_data
        except Exception as e:
            await self.error_handler.handle_error(e, {'operation': 'resume_parsing', 'resume_path': resume_path})
            raise
    
    @log_pipeline_stage(PipelineStage.JOB_SCRAPING)
    async def scrape_jobs(self, sites: List[str] = None) -> List[Dict[str, Any]]:
        """Scrape jobs with enhanced resilience and browser management"""
        if sites is None:
            sites = ['linkedin', 'wellfound']
        
        all_jobs = []
        
        for site in sites:
            try:
                logger.info(f"🔍 Scraping jobs from {site}...")
                
                # Use browser manager for scraping
                if site == 'linkedin':
                    jobs = await self.browser_manager.execute_operation(
                        self.linkedin_scraper.scrape_jobs
                    )
                elif site == 'wellfound':
                    jobs = await self.browser_manager.execute_operation(
                        self.wellfound_scraper.scrape_jobs
                    )
                else:
                    logger.warning(f"Unknown site: {site}")
                    continue
                
                # Handle CAPTCHA if detected
                if jobs is None:  # CAPTCHA detected
                    logger.warning(f"CAPTCHA detected on {site}, skipping...")
                    continue
                
                all_jobs.extend(jobs)
                logger.info(f"✅ Scraped {len(jobs)} jobs from {site}")
                
            except Exception as e:
                await self.error_handler.handle_error(e, {'operation': 'job_scraping', 'site': site})
                logger.error(f"❌ Failed to scrape {site}: {e}")
                continue
        
        logger.info(f"✅ Total jobs scraped: {len(all_jobs)}")
        return all_jobs
    
    @log_pipeline_stage(PipelineStage.GPT_FILTERING)
    async def filter_jobs(self, jobs: List[Dict[str, Any]], resume_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter jobs using GPT with enhanced resilience"""
        try:
            filtered_jobs = []
            
            for job in jobs:
                try:
                    # Use circuit breaker for GPT calls
                    result = await self.circuit_breaker_manager.call_with_circuit_breaker(
                        'gpt_api',
                        lambda: self.gpt_filter.evaluate_job(job, resume_data)
                    )
                    
                    if result and result.get('should_apply', False):
                        job['gpt_evaluation'] = result
                        job['cover_letter'] = result.get('cover_letter', '')
                        filtered_jobs.append(job)
                    
                except Exception as e:
                    await self.error_handler.handle_error(e, {
                        'operation': 'gpt_filtering',
                        'job_title': job.get('title', 'Unknown'),
                        'company': job.get('company', 'Unknown')
                    })
                    continue
            
            logger.info(f"✅ Filtered {len(filtered_jobs)} jobs from {len(jobs)} total")
            return filtered_jobs
            
        except Exception as e:
            await self.error_handler.handle_error(e, {'operation': 'gpt_filtering'})
            raise
    
    @log_pipeline_stage(PipelineStage.AUTO_APPLY)
    async def apply_to_jobs(self, jobs: List[Dict[str, Any]], resume_path: str) -> List[Dict[str, Any]]:
        """Apply to jobs with enhanced browser management and error handling"""
        applications = []
        
        for job in jobs:
            try:
                logger.info(f"📝 Applying to {job.get('title')} at {job.get('company')}")
                
                # Use browser manager for application
                result = await self.browser_manager.execute_operation(
                    self.applicator.apply_to_job,
                    job,
                    resume_path
                )
                
                if result:
                    applications.append({
                        'job': job,
                        'status': 'applied',
                        'timestamp': datetime.now().isoformat(),
                        'cover_letter': job.get('cover_letter', ''),
                        'resume_uploaded': True
                    })
                    logger.info(f"✅ Applied to {job.get('title')}")
                else:
                    applications.append({
                        'job': job,
                        'status': 'failed',
                        'timestamp': datetime.now().isoformat(),
                        'error_message': 'Application failed'
                    })
                    logger.warning(f"❌ Failed to apply to {job.get('title')}")
                
            except Exception as e:
                await self.error_handler.handle_error(e, {
                    'operation': 'auto_apply',
                    'job_title': job.get('title', 'Unknown'),
                    'company': job.get('company', 'Unknown')
                })
                
                applications.append({
                    'job': job,
                    'status': 'error',
                    'timestamp': datetime.now().isoformat(),
                    'error_message': str(e)
                })
                
                logger.error(f"❌ Error applying to {job.get('title')}: {e}")
                continue
        
        logger.info(f"✅ Applied to {len([a for a in applications if a['status'] == 'applied'])} jobs")
        return applications
    
    @log_pipeline_stage(PipelineStage.SHEETS_LOGGING)
    async def log_applications(self, applications: List[Dict[str, Any]]):
        """Log applications to Google Sheets with enhanced error handling"""
        try:
            for application in applications:
                try:
                    # Use enhanced sheets logger
                    success = await self.sheets_logger.log_application(application)
                    
                    if success:
                        logger.debug(f"✅ Logged application to {application['job'].get('title')}")
                    else:
                        logger.warning(f"⚠️ Failed to log application to {application['job'].get('title')}")
                
                except Exception as e:
                    await self.error_handler.handle_error(e, {
                        'operation': 'sheets_logging',
                        'job_title': application['job'].get('title', 'Unknown')
                    })
                    logger.error(f"❌ Error logging application: {e}")
                    continue
            
            logger.info(f"✅ Logged {len(applications)} applications to Google Sheets")
            
        except Exception as e:
            await self.error_handler.handle_error(e, {'operation': 'sheets_logging'})
            raise
    
    async def run_pipeline(self, resume_path: str = 'resume.pdf') -> Dict[str, Any]:
        """Run the complete job application pipeline with comprehensive resilience"""
        start_time = time.time()
        
        try:
            # Log pipeline start
            self.critical_path_logger.log_pipeline_start('ai_job_application', {
                'resume_path': resume_path,
                'timestamp': start_time
            })
            
            logger.info("🚀 Starting AI Job Application Pipeline...")
            
            # Parse resume
            resume_data = await self.parse_resume(resume_path)
            
            # Scrape jobs
            jobs = await self.scrape_jobs()
            
            if not jobs:
                logger.warning("⚠️ No jobs found, ending pipeline")
                return {'status': 'no_jobs_found', 'jobs_processed': 0}
            
            # Filter jobs
            filtered_jobs = await self.filter_jobs(jobs, resume_data)
            
            if not filtered_jobs:
                logger.warning("⚠️ No jobs passed filtering, ending pipeline")
                return {'status': 'no_jobs_filtered', 'jobs_processed': len(jobs)}
            
            # Apply to jobs
            applications = await self.apply_to_jobs(filtered_jobs, resume_path)
            
            # Log applications
            await self.log_applications(applications)
            
            # Update metrics
            self._update_pipeline_metrics(start_time, len(jobs), len(applications))
            
            # Log pipeline completion
            results = {
                'status': 'success',
                'jobs_scraped': len(jobs),
                'jobs_filtered': len(filtered_jobs),
                'applications_sent': len([a for a in applications if a['status'] == 'applied']),
                'duration': time.time() - start_time
            }
            
            self.critical_path_logger.log_pipeline_completion('ai_job_application', results)
            
            logger.info(f"✅ Pipeline completed successfully: {results}")
            return results
            
        except Exception as e:
            duration = time.time() - start_time
            self.critical_path_logger.log_pipeline_failure('ai_job_application', e)
            
            await self.error_handler.handle_error(e, {'operation': 'pipeline_execution'})
            logger.critical(f"❌ Pipeline failed after {duration:.2f}s: {e}")
            
            return {
                'status': 'failed',
                'error': str(e),
                'duration': duration
            }
    
    def _update_pipeline_metrics(self, start_time: float, jobs_processed: int, applications_sent: int):
        """Update pipeline metrics"""
        self.pipeline_metrics['total_runs'] += 1
        self.pipeline_metrics['total_jobs_processed'] += jobs_processed
        self.pipeline_metrics['total_applications_sent'] += applications_sent
        self.pipeline_metrics['last_run_time'] = start_time
        
        duration = time.time() - start_time
        if self.pipeline_metrics['average_run_duration'] == 0:
            self.pipeline_metrics['average_run_duration'] = duration
        else:
            self.pipeline_metrics['average_run_duration'] = (
                (self.pipeline_metrics['average_run_duration'] + duration) / 2
            )
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status"""
        return {
            'pipeline_metrics': self.pipeline_metrics,
            'error_metrics': self.error_handler.get_error_metrics(),
            'circuit_breaker_status': self.circuit_breaker_manager.get_health_status(),
            'browser_metrics': self.browser_manager.get_metrics(),
            'gpt_metrics': self.gpt_manager.get_metrics(),
            'cache_metrics': self.cache_manager.get_metrics(),
            'sheets_metrics': self.sheets_logger.get_metrics(),
            'captcha_metrics': self.captcha_handler.get_captcha_metrics(),
            'selector_health': self.selector_registry.get_health_report(),
            'critical_path_metrics': self.critical_path_logger.get_pipeline_metrics()
        }
    
    async def cleanup(self):
        """Clean up all resources"""
        try:
            logger.info("🧹 Cleaning up AI Job Bot resources...")
            
            # Clean up browser manager
            await self.browser_manager.cleanup()
            
            # Reset all managers
            reset_error_handler()
            reset_circuit_breaker_manager()
            reset_data_consistency_manager()
            reset_security_manager()
            reset_monitoring_manager()
            reset_db_optimizer()
            reset_gpt_manager()
            reset_cache_manager()
            reset_api_resilience_manager()
            reset_selector_registry()
            reset_captcha_handler()
            reset_sheets_logger()
            reset_browser_manager()
            reset_critical_path_logger()
            
            logger.info("✅ AI Job Bot cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")

async def main():
    """Main entry point with enhanced error handling"""
    bot = AIJobBot()
    
    try:
        await bot.initialize()
        
        # Run the pipeline
        results = await bot.run_pipeline()
        
        # Log system health
        health = await bot.get_system_health()
        logger.info(f"System Health: {json.dumps(health, indent=2)}")
        
        return results
        
    except Exception as e:
        logger.critical(f"❌ Fatal error in main: {e}")
        raise
    finally:
        await bot.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 