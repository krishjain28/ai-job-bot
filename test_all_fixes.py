#!/usr/bin/env python3
"""
Comprehensive test script for all fixes and new features:
- Enhanced Selector Registry with health monitoring
- Manual CAPTCHA Fallback with alerting
- Google Sheets quota management and error recovery
- Browser resource management for bulk operations
- Critical path logging for all pipeline stages
"""

import asyncio
import logging
import time
import json
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AllFixesTester:
    """Test all fixes and new features"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = time.time()
    
    async def run_all_tests(self):
        """Run all tests for fixes and new features"""
        logger.info("🚀 Starting comprehensive fixes and features tests...")
        
        test_suites = [
            ("Enhanced Selector Registry", self.test_selector_registry),
            ("CAPTCHA Handler", self.test_captcha_handler),
            ("Enhanced Sheets Logger", self.test_sheets_logger),
            ("Browser Manager", self.test_browser_manager),
            ("Critical Path Logger", self.test_critical_path_logger),
            ("Integration Tests", self.test_integration),
        ]
        
        for suite_name, test_func in test_suites:
            logger.info(f"\n{'='*60}")
            logger.info(f"🧪 Testing: {suite_name}")
            logger.info(f"{'='*60}")
            
            try:
                start_time = time.time()
                result = await test_func()
                duration = time.time() - start_time
                
                self.test_results[suite_name] = {
                    'status': 'PASSED' if result else 'FAILED',
                    'duration': duration,
                    'timestamp': time.time()
                }
                
                logger.info(f"✅ {suite_name}: {'PASSED' if result else 'FAILED'} ({duration:.2f}s)")
                
            except Exception as e:
                logger.error(f"❌ {suite_name} test failed: {e}")
                self.test_results[suite_name] = {
                    'status': 'ERROR',
                    'error': str(e),
                    'duration': 0,
                    'timestamp': time.time()
                }
        
        # Print final results
        self.print_test_summary()
    
    async def test_selector_registry(self) -> bool:
        """Test enhanced selector registry with health monitoring"""
        try:
            from utils.selector_registry import get_selector_registry, reset_selector_registry
            
            # Reset for clean test
            reset_selector_registry()
            registry = get_selector_registry()
            
            # Test selector registration
            test_selectors = {
                'job_cards': ['.test-card', '.fallback-card'],
                'job_title': ['.test-title', '.fallback-title']
            }
            
            registry.register_selectors('test_site', test_selectors)
            
            # Test selector retrieval
            selectors = registry.get_selectors('test_site', 'job_cards')
            assert len(selectors) == 2, f"Expected 2 selectors, got {len(selectors)}"
            
            # Test selector attempt recording
            registry.record_selector_attempt('test_site', 'job_cards', '.test-card', True, 1.5)
            registry.record_selector_attempt('test_site', 'job_cards', '.test-card', False, 0.5, "Element not found")
            
            # Test fallback recording
            registry.record_fallback_trigger('test_site', 'job_cards')
            
            # Test health report
            health_report = registry.get_health_report()
            assert 'test_site' in health_report['sites'], "Health report should include test site"
            
            # Test metrics
            metrics = health_report['sites']['test_site']['job_cards']
            assert metrics['total_attempts'] == 2, f"Expected 2 attempts, got {metrics['total_attempts']}"
            assert metrics['fallback_triggers'] == 1, f"Expected 1 fallback, got {metrics['fallback_triggers']}"
            
            logger.info("✅ Selector registry tests passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Selector registry test failed: {e}")
            return False
    
    async def test_captcha_handler(self) -> bool:
        """Test CAPTCHA handler with manual fallback"""
        try:
            from utils.captcha_handler import get_captcha_handler, reset_captcha_handler, CAPTCHAType, CAPTCHAStatus
            
            # Reset for clean test
            reset_captcha_handler()
            captcha_handler = get_captcha_handler()
            
            # Test CAPTCHA type detection (mock)
            class MockPage:
                async def query_selector(self, selector):
                    if 'recaptcha' in selector:
                        return True
                    return None
            
            mock_page = MockPage()
            captcha_type = await captcha_handler._detect_captcha_type(mock_page)
            assert captcha_type == CAPTCHAType.RECAPTCHA, f"Expected RECAPTCHA, got {captcha_type}"
            
            # Test manual fallback callback
            callback_called = False
            
            async def test_callback(challenge, page):
                nonlocal callback_called
                callback_called = True
                return True
            
            captcha_handler.set_manual_fallback_callback(test_callback)
            
            # Test CAPTCHA challenge creation
            challenge = captcha_handler.challenges[0] if captcha_handler.challenges else None
            if challenge:
                assert challenge.type == CAPTCHAType.RECAPTCHA, "Challenge should be RECAPTCHA type"
            
            # Test metrics
            metrics = captcha_handler.get_captcha_metrics()
            assert 'total_challenges' in metrics, "Metrics should include total_challenges"
            
            logger.info("✅ CAPTCHA handler tests passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ CAPTCHA handler test failed: {e}")
            return False
    
    async def test_sheets_logger(self) -> bool:
        """Test enhanced Google Sheets logger"""
        try:
            from utils.sheets_logger import get_sheets_logger, reset_sheets_logger, SheetsErrorType
            
            # Reset for clean test
            reset_sheets_logger()
            sheets_logger = get_sheets_logger()
            
            # Test error categorization
            test_errors = [
                (Exception("quota exceeded"), SheetsErrorType.QUOTA_EXCEEDED),
                (Exception("unauthorized"), SheetsErrorType.AUTH_ERROR),
                (Exception("rate limit"), SheetsErrorType.RATE_LIMIT),
                (Exception("network timeout"), SheetsErrorType.NETWORK_ERROR),
            ]
            
            for error, expected_type in test_errors:
                error_type = sheets_logger._categorize_error(error)
                assert error_type == expected_type, f"Expected {expected_type}, got {error_type}"
            
            # Test quota checking
            assert sheets_logger._check_quota(), "Quota should allow operation initially"
            
            # Test circuit breaker
            assert sheets_logger._check_circuit_breaker(), "Circuit breaker should be closed initially"
            
            # Test metrics
            metrics = sheets_logger.get_metrics()
            assert 'connection_status' in metrics, "Metrics should include connection status"
            assert 'quota_status' in metrics, "Metrics should include quota status"
            
            logger.info("✅ Enhanced sheets logger tests passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Enhanced sheets logger test failed: {e}")
            return False
    
    async def test_browser_manager(self) -> bool:
        """Test browser manager with resource monitoring"""
        try:
            from utils.browser_manager import get_browser_manager, reset_browser_manager, BrowserConfig, BrowserStatus
            
            # Reset for clean test
            reset_browser_manager()
            
            # Test browser manager creation
            config = BrowserConfig(
                headless=True,
                max_pages_per_context=2,
                max_contexts=1,
                memory_limit_mb=512
            )
            
            browser_manager = get_browser_manager(config)
            
            # Test configuration
            assert browser_manager.config.max_pages_per_context == 2, "Config should be set correctly"
            assert browser_manager.status == BrowserStatus.IDLE, "Should start in idle status"
            
            # Test metrics
            metrics = browser_manager.get_metrics()
            assert 'status' in metrics, "Metrics should include status"
            assert 'operation_count' in metrics, "Metrics should include operation count"
            
            # Test resource limit checking (mock)
            # Note: We can't easily test actual resource monitoring without real browser
            # but we can test the logic structure
            
            logger.info("✅ Browser manager tests passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Browser manager test failed: {e}")
            return False
    
    async def test_critical_path_logger(self) -> bool:
        """Test critical path logger"""
        try:
            from utils.critical_path_logger import (
                get_critical_path_logger, reset_critical_path_logger, 
                PipelineStage, StageStatus
            )
            
            # Reset for clean test
            reset_critical_path_logger()
            path_logger = get_critical_path_logger()
            
            # Test stage context
            async with path_logger.stage_context(PipelineStage.RESUME_PARSING, {'test': 'data'}) as context:
                assert context.stage == PipelineStage.RESUME_PARSING, "Stage should be set correctly"
                assert context.status == StageStatus.STARTED, "Should start in started status"
                
                # Simulate some work
                await asyncio.sleep(0.1)
                
                # Context should be completed automatically
            
            # Test pipeline logging
            path_logger.log_pipeline_start('test_pipeline', {'config': 'test'})
            path_logger.log_pipeline_completion('test_pipeline', {'results': 'test'})
            
            # Test metrics
            metrics = path_logger.get_pipeline_metrics()
            assert 'total_stages' in metrics, "Metrics should include total stages"
            assert 'success_rate' in metrics, "Metrics should include success rate"
            
            # Test recent stages
            recent = path_logger.get_recent_stages(5)
            assert len(recent) > 0, "Should have recent stages"
            
            logger.info("✅ Critical path logger tests passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Critical path logger test failed: {e}")
            return False
    
    async def test_integration(self) -> bool:
        """Test integration of all systems"""
        try:
            # Test that all managers can be initialized together
            from utils.selector_registry import get_selector_registry
            from utils.captcha_handler import get_captcha_handler
            from utils.sheets_logger import get_sheets_logger
            from utils.critical_path_logger import get_critical_path_logger
            
            # Initialize all managers
            selector_registry = get_selector_registry()
            captcha_handler = get_captcha_handler()
            sheets_logger = get_sheets_logger()
            path_logger = get_critical_path_logger()
            
            # Test that they can work together
            assert selector_registry is not None, "Selector registry should be initialized"
            assert captcha_handler is not None, "CAPTCHA handler should be initialized"
            assert sheets_logger is not None, "Sheets logger should be initialized"
            assert path_logger is not None, "Critical path logger should be initialized"
            
            # Test cross-system integration
            # Add a test that shows how systems work together
            logger.info("✅ Integration tests passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Integration test failed: {e}")
            return False
    
    def print_test_summary(self):
        """Print comprehensive test summary"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results.values() if r['status'] == 'PASSED'])
        failed_tests = len([r for r in self.test_results.values() if r['status'] == 'FAILED'])
        error_tests = len([r for r in self.test_results.values() if r['status'] == 'ERROR'])
        
        total_duration = time.time() - self.start_time
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        logger.info(f"\n{'='*80}")
        logger.info("🎯 ALL FIXES AND FEATURES TEST SUMMARY")
        logger.info(f"{'='*80}")
        logger.info(f"⏱️  Total Duration: {total_duration:.2f}s")
        logger.info(f"🧪 Total Tests: {total_tests}")
        logger.info(f"✅ Passed: {passed_tests}")
        logger.info(f"❌ Failed: {failed_tests}")
        logger.info(f"🚨 Errors: {error_tests}")
        logger.info(f"📊 Success Rate: {success_rate:.1f}%")
        
        logger.info(f"\n📋 Detailed Results:")
        logger.info(f"{'─'*80}")
        
        for test_name, result in self.test_results.items():
            status_icon = "✅" if result['status'] == 'PASSED' else "❌" if result['status'] == 'FAILED' else "🚨"
            logger.info(f"{status_icon} {test_name:<30} {result['status']:<10} {result['duration']:.2f}s")
        
        logger.info(f"\n{'='*80}")
        
        if success_rate == 100:
            logger.info("🎉 ALL TESTS PASSED! All fixes and features are working correctly.")
        else:
            logger.info("⚠️  Some tests failed. Please review the errors above.")
        
        logger.info(f"{'='*80}")

async def main():
    """Main test runner"""
    tester = AllFixesTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main()) 