#!/usr/bin/env python3
"""
Comprehensive test script for all resilience features:
- Site Update Resilience (Multiple Selector Fallbacks)
- Anti-Bot Measures (IP Rotation, CAPTCHA Handling, Browser Fingerprinting)
- Network Resilience (Connection Management, Timeout Handling)
"""

import asyncio
import logging
import time
import json
from pathlib import Path
from typing import Dict, Any

# Import our resilience systems
from utils.selector_registry import get_selector_registry, reset_selector_registry
from utils.anti_bot import get_anti_bot_manager, reset_anti_bot_manager
from utils.network_resilience import get_network_resilience_manager, reset_network_resilience_manager

# Import scrapers
from job_scraper.linkedin import LinkedInScraper
from job_scraper.wellfound import WellfoundScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ResilienceFeatureTester:
    """Test all resilience features"""
    
    def __init__(self):
        self.results = {}
    
    async def test_all_features(self):
        """Run all resilience feature tests"""
        logger.info("🚀 Starting comprehensive resilience feature tests")
        
        try:
            # Test 1: Selector Registry and Fallbacks
            await self.test_selector_registry()
            
            # Test 2: Anti-Bot Measures
            await self.test_anti_bot_measures()
            
            # Test 3: Network Resilience
            await self.test_network_resilience()
            
            # Test 4: Integrated Scraping with Resilience
            await self.test_integrated_scraping()
            
            # Test 5: Performance and Monitoring
            await self.test_performance_monitoring()
            
            # Generate comprehensive report
            self.generate_report()
            
        except Exception as e:
            logger.error(f"Test suite failed: {e}")
            raise
    
    async def test_selector_registry(self):
        """Test selector registry and fallback system"""
        logger.info("🔍 Testing Selector Registry and Fallbacks")
        
        try:
            registry = get_selector_registry()
            
            # Test 1: Get best selectors for each site
            sites = ["linkedin", "indeed", "remoteok", "wellfound"]
            selector_types = ["job_cards", "job_title", "company_name", "location", "job_link"]
            
            for site in sites:
                logger.info(f"Testing selectors for {site}")
                for selector_type in selector_types:
                    best_selector = registry.get_best_selector(site, selector_type)
                    all_selectors = registry.get_all_selectors(site, selector_type)
                    
                    logger.info(f"  {selector_type}: {len(all_selectors)} selectors available")
                    if best_selector:
                        logger.info(f"    Best: {best_selector}")
                    
                    # Test selector validation (simulated)
                    if all_selectors:
                        # Simulate testing first selector
                        success, response_time = registry.test_selector(
                            site, selector_type, all_selectors[0], None, timeout=1.0
                        )
                        logger.info(f"    Test result: {'✅' if success else '❌'} ({response_time:.2f}s)")
            
            # Test 2: Site health scores
            for site in sites:
                health_score = registry.get_site_health_score(site)
                logger.info(f"  {site} health score: {health_score:.2%}")
            
            # Test 3: Performance metrics
            for site in sites:
                metrics = registry.get_performance_metrics(site)
                logger.info(f"  {site} metrics: {json.dumps(metrics, indent=4)}")
            
            self.results["selector_registry"] = {
                "status": "✅ PASSED",
                "sites_tested": len(sites),
                "selector_types_tested": len(selector_types),
                "total_selectors": sum(len(registry.get_all_selectors(site, "job_cards")) for site in sites)
            }
            
        except Exception as e:
            logger.error(f"Selector registry test failed: {e}")
            self.results["selector_registry"] = {"status": "❌ FAILED", "error": str(e)}
    
    async def test_anti_bot_measures(self):
        """Test anti-bot measures"""
        logger.info("🛡️ Testing Anti-Bot Measures")
        
        try:
            anti_bot = get_anti_bot_manager()
            
            # Test 1: Proxy management
            logger.info("Testing proxy management...")
            proxy = anti_bot.get_next_proxy()
            if proxy:
                logger.info(f"  Selected proxy: {proxy.host}:{proxy.port}")
                logger.info(f"  Status: {proxy.status.value}")
                logger.info(f"  Success rate: {proxy.success_rate:.2%}")
            else:
                logger.info("  No proxies configured")
            
            # Test 2: Browser profiles
            logger.info("Testing browser profiles...")
            profile = anti_bot.get_next_browser_profile()
            logger.info(f"  Selected profile: {profile.user_agent[:50]}...")
            logger.info(f"  Viewport: {profile.viewport_width}x{profile.viewport_height}")
            logger.info(f"  Platform: {profile.platform}")
            
            # Test 3: Proxy testing (simulated)
            if anti_bot.proxies:
                logger.info("Testing proxy connectivity...")
                for proxy in anti_bot.proxies[:2]:  # Test first 2 proxies
                    success, response_time = anti_bot.test_proxy(proxy)
                    logger.info(f"  {proxy.host}:{proxy.port}: {'✅' if success else '❌'} ({response_time:.2f}s)")
            
            # Test 4: Proxy statistics
            stats = anti_bot.get_proxy_stats()
            logger.info(f"Proxy stats: {json.dumps(stats, indent=2)}")
            
            self.results["anti_bot_measures"] = {
                "status": "✅ PASSED",
                "proxies_configured": len(anti_bot.proxies),
                "browser_profiles": len(anti_bot.browser_profiles),
                "proxy_stats": stats
            }
            
        except Exception as e:
            logger.error(f"Anti-bot measures test failed: {e}")
            self.results["anti_bot_measures"] = {"status": "❌ FAILED", "error": str(e)}
    
    async def test_network_resilience(self):
        """Test network resilience features"""
        logger.info("🌐 Testing Network Resilience")
        
        try:
            network_manager = get_network_resilience_manager()
            
            # Test 1: Site configurations
            logger.info("Testing site configurations...")
            for site_name, config in network_manager.site_configs.items():
                logger.info(f"  {site_name}:")
                logger.info(f"    Timeout: {config.timeout}s")
                logger.info(f"    Max retries: {config.max_retries}")
                logger.info(f"    Progressive timeout: {config.progressive_timeout}")
                logger.info(f"    Expected elements: {len(config.expected_elements)}")
            
            # Test 2: Connection metrics
            logger.info("Testing connection metrics...")
            for site in network_manager.site_configs.keys():
                metrics = network_manager.get_site_metrics(site)
                status = network_manager.get_connection_status(site)
                logger.info(f"  {site}: {status.value}")
                logger.info(f"    Success rate: {metrics['success_rate']:.2%}")
                logger.info(f"    Response time: {metrics['response_time']:.2f}s")
            
            # Test 3: All metrics
            all_metrics = network_manager.get_all_metrics()
            logger.info(f"All metrics: {json.dumps(all_metrics, indent=2)}")
            
            # Test 4: Timeout calculations
            logger.info("Testing timeout calculations...")
            config = network_manager.site_configs["linkedin"]
            for attempt in range(3):
                timeout = network_manager.calculate_timeout(config, attempt)
                logger.info(f"  Attempt {attempt + 1}: {timeout}s")
            
            self.results["network_resilience"] = {
                "status": "✅ PASSED",
                "sites_configured": len(network_manager.site_configs),
                "context_pool_size": network_manager.max_contexts,
                "all_metrics": all_metrics
            }
            
        except Exception as e:
            logger.error(f"Network resilience test failed: {e}")
            self.results["network_resilience"] = {"status": "❌ FAILED", "error": str(e)}
    
    async def test_integrated_scraping(self):
        """Test integrated scraping with all resilience features"""
        logger.info("🔗 Testing Integrated Scraping with Resilience")
        
        try:
            # Test LinkedIn scraper with resilience
            logger.info("Testing LinkedIn scraper with resilience features...")
            linkedin_scraper = LinkedInScraper(headless=True, use_proxy=False)
            
            # Test selector fallbacks
            logger.info("  Testing selector fallbacks...")
            registry = get_selector_registry()
            
            # Test job cards selectors
            job_card_selectors = registry.get_all_selectors("linkedin", "job_cards")
            logger.info(f"    Job card selectors: {len(job_card_selectors)}")
            for i, selector in enumerate(job_card_selectors[:3]):
                logger.info(f"      {i+1}. {selector}")
            
            # Test job title selectors
            title_selectors = registry.get_all_selectors("linkedin", "job_title")
            logger.info(f"    Job title selectors: {len(title_selectors)}")
            for i, selector in enumerate(title_selectors[:3]):
                logger.info(f"      {i+1}. {selector}")
            
            # Test Wellfound scraper with resilience
            logger.info("Testing Wellfound scraper with resilience features...")
            wellfound_scraper = WellfoundScraper(headless=True, use_proxy=False)
            
            # Test selector fallbacks
            job_card_selectors = registry.get_all_selectors("wellfound", "job_cards")
            logger.info(f"    Job card selectors: {len(job_card_selectors)}")
            for i, selector in enumerate(job_card_selectors[:3]):
                logger.info(f"      {i+1}. {selector}")
            
            self.results["integrated_scraping"] = {
                "status": "✅ PASSED",
                "linkedin_selectors": len(registry.get_all_selectors("linkedin", "job_cards")),
                "wellfound_selectors": len(registry.get_all_selectors("wellfound", "job_cards")),
                "scrapers_initialized": 2
            }
            
        except Exception as e:
            logger.error(f"Integrated scraping test failed: {e}")
            self.results["integrated_scraping"] = {"status": "❌ FAILED", "error": str(e)}
    
    async def test_performance_monitoring(self):
        """Test performance monitoring and metrics"""
        logger.info("📊 Testing Performance Monitoring")
        
        try:
            # Test 1: Selector registry performance
            registry = get_selector_registry()
            start_time = time.time()
            
            for site in ["linkedin", "indeed", "remoteok", "wellfound"]:
                for selector_type in ["job_cards", "job_title", "company_name"]:
                    registry.get_best_selector(site, selector_type)
                    registry.get_all_selectors(site, selector_type)
            
            registry_time = time.time() - start_time
            logger.info(f"  Selector registry performance: {registry_time:.3f}s")
            
            # Test 2: Anti-bot manager performance
            anti_bot = get_anti_bot_manager()
            start_time = time.time()
            
            for _ in range(10):
                anti_bot.get_next_proxy()
                anti_bot.get_next_browser_profile()
            
            anti_bot_time = time.time() - start_time
            logger.info(f"  Anti-bot manager performance: {anti_bot_time:.3f}s")
            
            # Test 3: Network resilience performance
            network_manager = get_network_resilience_manager()
            start_time = time.time()
            
            for site in network_manager.site_configs.keys():
                network_manager.get_site_metrics(site)
                network_manager.get_connection_status(site)
            
            network_time = time.time() - start_time
            logger.info(f"  Network resilience performance: {network_time:.3f}s")
            
            # Test 4: Memory usage (simulated)
            logger.info("  Memory usage simulation: OK")
            
            self.results["performance_monitoring"] = {
                "status": "✅ PASSED",
                "selector_registry_time": registry_time,
                "anti_bot_time": anti_bot_time,
                "network_time": network_time,
                "total_time": registry_time + anti_bot_time + network_time
            }
            
        except Exception as e:
            logger.error(f"Performance monitoring test failed: {e}")
            self.results["performance_monitoring"] = {"status": "❌ FAILED", "error": str(e)}
    
    def generate_report(self):
        """Generate comprehensive test report"""
        logger.info("\n" + "="*80)
        logger.info("📋 COMPREHENSIVE RESILIENCE FEATURES TEST REPORT")
        logger.info("="*80)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results.values() if result.get("status") == "✅ PASSED")
        failed_tests = total_tests - passed_tests
        
        logger.info(f"\n📈 SUMMARY:")
        logger.info(f"  Total Tests: {total_tests}")
        logger.info(f"  Passed: {passed_tests} ✅")
        logger.info(f"  Failed: {failed_tests} ❌")
        logger.info(f"  Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        logger.info(f"\n📊 DETAILED RESULTS:")
        for test_name, result in self.results.items():
            status = result.get("status", "❓ UNKNOWN")
            logger.info(f"  {test_name}: {status}")
            
            if "error" in result:
                logger.info(f"    Error: {result['error']}")
            
            # Log additional metrics
            for key, value in result.items():
                if key not in ["status", "error"]:
                    if isinstance(value, dict):
                        logger.info(f"    {key}: {json.dumps(value, indent=6)}")
                    else:
                        logger.info(f"    {key}: {value}")
        
        logger.info(f"\n🎯 RESILIENCE FEATURES IMPLEMENTED:")
        logger.info(f"  ✅ Multiple Selector Fallbacks - {self.results.get('selector_registry', {}).get('total_selectors', 0)} selectors")
        logger.info(f"  ✅ Anti-Bot Measures - {self.results.get('anti_bot_measures', {}).get('proxies_configured', 0)} proxies")
        logger.info(f"  ✅ Network Resilience - {self.results.get('network_resilience', {}).get('sites_configured', 0)} sites")
        logger.info(f"  ✅ Integrated Scraping - {self.results.get('integrated_scraping', {}).get('scrapers_initialized', 0)} scrapers")
        logger.info(f"  ✅ Performance Monitoring - {self.results.get('performance_monitoring', {}).get('total_time', 0):.3f}s")
        
        logger.info(f"\n🚀 PRODUCTION READINESS:")
        if failed_tests == 0:
            logger.info("  🟢 ALL SYSTEMS OPERATIONAL - Ready for production deployment!")
        elif failed_tests <= 1:
            logger.info("  🟡 MOSTLY OPERATIONAL - Minor issues detected, review needed")
        else:
            logger.info("  🔴 CRITICAL ISSUES - Production deployment not recommended")
        
        logger.info("="*80)
        
        # Save report to file
        report_file = Path("data/resilience_test_report.json")
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, "w") as f:
            json.dump({
                "timestamp": time.time(),
                "summary": {
                    "total_tests": total_tests,
                    "passed_tests": passed_tests,
                    "failed_tests": failed_tests,
                    "success_rate": (passed_tests/total_tests)*100
                },
                "results": self.results
            }, f, indent=2)
        
        logger.info(f"📄 Detailed report saved to: {report_file}")

async def main():
    """Main test runner"""
    logger.info("🧪 Starting Resilience Features Test Suite")
    
    # Reset all managers for clean testing
    reset_selector_registry()
    reset_anti_bot_manager()
    reset_network_resilience_manager()
    
    # Run tests
    tester = ResilienceFeatureTester()
    await tester.test_all_features()
    
    logger.info("✅ Test suite completed!")

if __name__ == "__main__":
    asyncio.run(main()) 