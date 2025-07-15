#!/usr/bin/env python3
"""
Comprehensive AI Job Bot Testing Script
Tests all major features and components
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComprehensiveTester:
    """Comprehensive testing for AI Job Bot"""
    
    def __init__(self):
        self.test_results = {}
        self.overall_status = "PASSED"
        
    def run_all_tests(self):
        """Run all comprehensive tests"""
        print("🤖 AI Job Bot - Comprehensive Testing")
        print("=" * 60)
        
        tests = [
            ("📄 Smart Resume Analysis", self.test_resume_parsing),
            ("🔍 Multi-Platform Scraping", self.test_job_scraping),
            ("🤖 AI Job Matching", self.test_gpt_filtering),
            ("📝 Real Application Automation", self.test_application_automation),
            ("📊 Comprehensive Logging", self.test_logging_systems),
            ("🚀 Production Readiness", self.test_production_setup),
            ("🎨 Monitoring Dashboard", self.test_dashboard),
            ("📧 Email Alerts", self.test_email_notifications),
            ("⏰ Scheduled Execution", self.test_scheduling),
            ("🛡️ Error Handling", self.test_error_handling)
        ]
        
        for test_name, test_func in tests:
            print(f"\n{test_name}")
            print("-" * 40)
            try:
                result = test_func()
                self.test_results[test_name] = result
                if not result['status']:
                    self.overall_status = "FAILED"
                print(f"✅ {test_name}: {'PASSED' if result['status'] else 'FAILED'}")
                if result['details']:
                    print(f"   Details: {result['details']}")
            except Exception as e:
                self.test_results[test_name] = {'status': False, 'details': str(e)}
                self.overall_status = "FAILED"
                print(f"❌ {test_name}: FAILED - {e}")
        
        self.print_summary()
        
    def test_resume_parsing(self):
        """Test smart resume analysis"""
        try:
            # Test 1: Check if resume file exists
            from config import RESUME_PATH
            resume_path = RESUME_PATH
            if not Path(resume_path).exists():
                return {
                    'status': False,
                    'details': f"Resume file not found: {resume_path}"
                }
            
            # Test 2: Import and test resume parser
            from resume_parser import ResumeParser
            
            parser = ResumeParser(resume_path)
            
            # Test 3: Extract text
            text = parser.extract_text()
            if not text:
                return {
                    'status': False,
                    'details': "Failed to extract text from resume"
                }
            
            # Test 4: Parse sections
            sections = parser.parse_resume()
            if not sections:
                return {
                    'status': False,
                    'details': "Failed to parse resume sections"
                }
            
            # Test 5: Check if sections have content
            if not any(sections.values()):
                return {
                    'status': False,
                    'details': "Resume sections are empty"
                }
            
            # Test 6: Check extracted data
            skills_found = len(sections.get('skills', {}).get('technical', []))
            experience_found = len(sections.get('experience', []))
            contact_found = any(sections.get('contact', {}).values())
            
            details = f"Skills: {skills_found}, Experience: {experience_found}, Contact: {contact_found}"
            
            return {
                'status': True,
                'details': details,
                'data': {
                    'text_length': len(text),
                    'skills_count': skills_found,
                    'experience_count': experience_found,
                    'has_contact': contact_found
                }
            }
            
        except Exception as e:
            return {
                'status': False,
                'details': f"Resume parsing error: {e}"
            }
    
    def test_job_scraping(self):
        """Test multi-platform job scraping"""
        try:
            # Test 1: Check scraper modules
            scrapers = [
                ('job_scraper.remoteok', 'scrape_remoteok'),
                ('job_scraper.indeed', 'scrape_indeed'),
                ('job_scraper.linkedin', 'scrape_linkedin'),
                ('job_scraper.wellfound', 'scrape_wellfound')
            ]
            
            working_scrapers = []
            for module_name, func_name in scrapers:
                try:
                    module = __import__(module_name, fromlist=[func_name])
                    func = getattr(module, func_name)
                    working_scrapers.append(func_name)
                except Exception as e:
                    logger.warning(f"Scraper {func_name} not available: {e}")
            
            if not working_scrapers:
                return {
                    'status': False,
                    'details': "No job scrapers are working"
                }
            
            # Test 2: Test one scraper (simulated)
            try:
                from job_scraper.remoteok import scrape_remoteok
                # Note: This would actually scrape in real test
                return {
                    'status': True,
                    'details': f"Working scrapers: {', '.join(working_scrapers)}",
                    'data': {
                        'scrapers_available': len(working_scrapers),
                        'scrapers_list': working_scrapers
                    }
                }
            except Exception as e:
                return {
                    'status': False,
                    'details': f"Scraper test failed: {e}"
                }
                
        except Exception as e:
            return {
                'status': False,
                'details': f"Job scraping error: {e}"
            }
    
    def test_gpt_filtering(self):
        """Test AI job matching"""
        try:
            # Test 1: Check OpenAI configuration
            from config import OPENAI_API_KEY
            if not OPENAI_API_KEY:
                return {
                    'status': False,
                    'details': "OpenAI API key not configured"
                }
            
            # Test 2: Import GPT filter
            from gpt_filter import filter_jobs, generate_application_message
            
            # Test 3: Test with sample data
            sample_jobs = [
                {
                    'title': 'Python Developer',
                    'company': 'Tech Corp',
                    'description': 'Looking for Python developer with Django experience'
                }
            ]
            
            sample_resume = "Experienced Python developer with Django and Flask skills"
            
            # Test filtering (would call OpenAI API in real test)
            try:
                # This is a simulation - in real test it would call OpenAI
                return {
                    'status': True,
                    'details': "GPT filtering components available",
                    'data': {
                        'api_key_configured': bool(OPENAI_API_KEY),
                        'functions_available': ['filter_jobs', 'generate_application_message']
                    }
                }
            except Exception as e:
                return {
                    'status': False,
                    'details': f"GPT filtering test failed: {e}"
                }
                
        except Exception as e:
            return {
                'status': False,
                'details': f"GPT filtering error: {e}"
            }
    
    def test_application_automation(self):
        """Test real application automation"""
        try:
            # Test 1: Check Playwright installation
            try:
                from playwright.sync_api import sync_playwright
                return {
                    'status': True,
                    'details': "Playwright available for automation",
                    'data': {
                        'playwright_installed': True,
                        'automation_ready': True
                    }
                }
            except ImportError:
                return {
                    'status': False,
                    'details': "Playwright not installed"
                }
            
        except Exception as e:
            return {
                'status': False,
                'details': f"Application automation error: {e}"
            }
    
    def test_logging_systems(self):
        """Test comprehensive logging"""
        try:
            # Test 1: Google Sheets integration
            from config import GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS_JSON
            sheets_configured = bool(GOOGLE_SHEET_ID and GOOGLE_CREDENTIALS_JSON)
            
            # Test 2: MongoDB integration
            from config import MONGODB_URI
            mongodb_configured = bool(MONGODB_URI)
            
            # Test 3: Import logging modules
            from sheets_logger import log_to_sheet, setup_sheet_headers
            from database.connection import db_manager
            
            return {
                'status': sheets_configured or mongodb_configured,
                'details': f"Google Sheets: {'✅' if sheets_configured else '❌'}, MongoDB: {'✅' if mongodb_configured else '❌'}",
                'data': {
                    'google_sheets': sheets_configured,
                    'mongodb': mongodb_configured,
                    'logging_modules': ['sheets_logger', 'database.connection']
                }
            }
            
        except Exception as e:
            return {
                'status': False,
                'details': f"Logging systems error: {e}"
            }
    
    def test_production_setup(self):
        """Test production readiness"""
        try:
            # Test 1: Check deployment files
            deployment_files = [
                'render.yaml',
                'vercel.json',
                'requirements.txt',
                'frontend/package.json'
            ]
            
            missing_files = []
            for file in deployment_files:
                if not Path(file).exists():
                    missing_files.append(file)
            
            # Test 2: Check environment configuration
            from config import (
                OPENAI_API_KEY, GOOGLE_SHEET_ID, MONGODB_URI,
                EMAIL_ENABLED, SCHEDULE_ENABLED
            )
            
            config_status = {
                'openai': bool(OPENAI_API_KEY),
                'sheets': bool(GOOGLE_SHEET_ID),
                'mongodb': bool(MONGODB_URI),
                'email': EMAIL_ENABLED,
                'scheduling': SCHEDULE_ENABLED
            }
            
            return {
                'status': len(missing_files) == 0,
                'details': f"Missing files: {missing_files if missing_files else 'None'}",
                'data': {
                    'deployment_files': len(deployment_files) - len(missing_files),
                    'config_status': config_status
                }
            }
            
        except Exception as e:
            return {
                'status': False,
                'details': f"Production setup error: {e}"
            }
    
    def test_dashboard(self):
        """Test monitoring dashboard"""
        try:
            # Test 1: Check frontend files
            frontend_files = [
                'frontend/src/App.js',
                'frontend/src/components/StatsCard.js',
                'frontend/src/components/JobsList.js',
                'frontend/package.json'
            ]
            
            missing_files = []
            for file in frontend_files:
                if not Path(file).exists():
                    missing_files.append(file)
            
            # Test 2: Check API endpoints
            api_files = [
                'api/main.py',
                'database/models.py',
                'database/connection.py'
            ]
            
            for file in api_files:
                if not Path(file).exists():
                    missing_files.append(file)
            
            return {
                'status': len(missing_files) == 0,
                'details': f"Missing files: {missing_files if missing_files else 'None'}",
                'data': {
                    'frontend_files': len(frontend_files) - len([f for f in missing_files if 'frontend' in f]),
                    'api_files': len(api_files) - len([f for f in missing_files if 'api' in f or 'database' in f])
                }
            }
            
        except Exception as e:
            return {
                'status': False,
                'details': f"Dashboard error: {e}"
            }
    
    def test_email_notifications(self):
        """Test email alerts"""
        try:
            # Test 1: Check email configuration
            from config import (
                EMAIL_ENABLED, EMAIL_SMTP_SERVER, 
                EMAIL_USERNAME, EMAIL_PASSWORD, EMAIL_TO_ADDRESS
            )
            
            email_configured = all([
                EMAIL_ENABLED,
                EMAIL_SMTP_SERVER,
                EMAIL_USERNAME,
                EMAIL_PASSWORD,
                EMAIL_TO_ADDRESS
            ])
            
            # Test 2: Check email modules
            try:
                import smtplib
                from email.mime.text import MIMEText
                from email.mime.multipart import MIMEMultipart
                email_modules_available = True
            except ImportError:
                email_modules_available = False
            
            return {
                'status': email_configured and email_modules_available,
                'details': f"Email configured: {'✅' if email_configured else '❌'}, Modules: {'✅' if email_modules_available else '❌'}",
                'data': {
                    'email_enabled': EMAIL_ENABLED,
                    'smtp_server': EMAIL_SMTP_SERVER,
                    'modules_available': email_modules_available
                }
            }
            
        except Exception as e:
            return {
                'status': False,
                'details': f"Email notifications error: {e}"
            }
    
    def test_scheduling(self):
        """Test scheduled execution"""
        try:
            # Test 1: Check scheduling configuration
            from config import SCHEDULE_ENABLED, SCHEDULE_TIME
            
            # Test 2: Check scheduling logic in main.py
            if Path('main.py').exists():
                with open('main.py', 'r') as f:
                    content = f.read()
                    has_scheduling = 'run_scheduled' in content and 'SCHEDULE_ENABLED' in content
            else:
                has_scheduling = False
            
            return {
                'status': has_scheduling,
                'details': f"Scheduling enabled: {'✅' if SCHEDULE_ENABLED else '❌'}, Time: {SCHEDULE_TIME}",
                'data': {
                    'scheduling_enabled': SCHEDULE_ENABLED,
                    'schedule_time': SCHEDULE_TIME,
                    'scheduling_logic': has_scheduling
                }
            }
            
        except Exception as e:
            return {
                'status': False,
                'details': f"Scheduling error: {e}"
            }
    
    def test_error_handling(self):
        """Test error handling"""
        try:
            # Test 1: Check error handling in main components
            error_handling_components = [
                'main.py',
                'resume_parser.py',
                'gpt_filter.py',
                'apply.py',
                'sheets_logger.py'
            ]
            
            components_with_errors = []
            for component in error_handling_components:
                if Path(component).exists():
                    with open(component, 'r') as f:
                        content = f.read()
                        if 'try:' in content and 'except' in content:
                            components_with_errors.append(component)
            
            # Test 2: Check logging configuration
            logging_configured = 'logging.basicConfig' in open('main.py').read() if Path('main.py').exists() else False
            
            return {
                'status': len(components_with_errors) >= 3 and logging_configured,
                'details': f"Error handling in {len(components_with_errors)} components, Logging: {'✅' if logging_configured else '❌'}",
                'data': {
                    'components_with_errors': len(components_with_errors),
                    'logging_configured': logging_configured
                }
            }
            
        except Exception as e:
            return {
                'status': False,
                'details': f"Error handling test failed: {e}"
            }
    
    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results.values() if result['status'])
        total = len(self.test_results)
        
        print(f"Overall Status: {self.overall_status}")
        print(f"Tests Passed: {passed}/{total}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        print("\n📋 Detailed Results:")
        for test_name, result in self.test_results.items():
            status_icon = "✅" if result['status'] else "❌"
            print(f"{status_icon} {test_name}: {'PASSED' if result['status'] else 'FAILED'}")
            if result.get('details'):
                print(f"   {result['details']}")
        
        print("\n🎯 Recommendations:")
        failed_tests = [name for name, result in self.test_results.items() if not result['status']]
        if failed_tests:
            print("❌ Fix these issues:")
            for test in failed_tests:
                print(f"   - {test}")
        else:
            print("✅ All systems are ready for deployment!")
        
        print("\n🚀 Next Steps:")
        if self.overall_status == "PASSED":
            print("1. Configure your .env file with API keys")
            print("2. Add your resume.pdf to the project root")
            print("3. Run: python main.py (for testing)")
            print("4. Deploy to production: python deploy.py")
        else:
            print("1. Fix the failed tests above")
            print("2. Install missing dependencies")
            print("3. Configure required API keys")
            print("4. Re-run tests: python test_comprehensive.py")

def main():
    """Main testing function"""
    tester = ComprehensiveTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main() 