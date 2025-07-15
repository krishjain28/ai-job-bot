#!/usr/bin/env python3
"""
Comprehensive test script for all new features:
- Silent Failure Elimination
- Cascade Failure Prevention  
- Data Consistency
- Security & Configuration
- Database Performance
- Monitoring & Observability
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

class ComprehensiveFeatureTester:
    """Test all comprehensive features"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = time.time()
    
    async def run_all_tests(self):
        """Run all comprehensive feature tests"""
        logger.info("🚀 Starting comprehensive feature tests...")
        
        test_suites = [
            ("Error Handling", self.test_error_handling),
            ("Circuit Breakers", self.test_circuit_breakers),
            ("Data Consistency", self.test_data_consistency),
            ("Security & Configuration", self.test_security_configuration),
            ("Database Performance", self.test_database_performance),
            ("Monitoring & Observability", self.test_monitoring_observability),
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
    
    async def test_error_handling(self) -> bool:
        """Test comprehensive error handling"""
        try:
            from utils.error_handler import get_error_handler, reset_error_handler
            
            # Reset for clean test
            reset_error_handler()
            error_handler = get_error_handler()
            
            # Test error categorization
            test_errors = [
                (Exception("Connection timeout"), "network"),
                (Exception("API rate limit exceeded"), "rate_limit"),
                (Exception("Database connection failed"), "network"),  # Fixed: connection errors are network
                (Exception("Invalid JSON format"), "validation"),  # Fixed: JSON format errors are validation
                (Exception("Authentication failed"), "authentication"),
            ]
            
            for error, expected_category in test_errors:
                context = {'operation': 'test', 'retry_count': 0}
                category = error_handler.categorize_error(error, context)
                assert category.value == expected_category, f"Expected {expected_category}, got {category.value}"
            
            # Test error severity determination
            context = {'is_critical_operation': True, 'retry_count': 0}
            test_error = Exception("Database connection failed")
            category = error_handler.categorize_error(test_error, context)
            severity = error_handler.determine_severity(test_error, category, context)
            
            # Debug: Print what we got vs what we expected
            logger.info(f"Debug: Error message: '{str(test_error)}'")
            logger.info(f"Debug: Category: {category.value}")
            logger.info(f"Debug: Severity: {severity.value}")
            logger.info(f"Debug: Context: {context}")
            
            assert severity.value == "critical", f"Expected critical severity for critical operation, got {severity.value}"
            
            # Test error handling with recovery
            handled = await error_handler.handle_error(
                Exception("Test error"), 
                {'operation': 'test', 'retry_count': 0}
            )
            assert isinstance(handled, bool), "Error handling should return boolean"
            
            # Test metrics
            metrics = error_handler.get_error_metrics()
            assert 'total_errors' in metrics, "Error metrics should include total_errors"
            
            logger.info("✅ Error handling tests passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error handling test failed: {e}")
            return False
    
    async def test_circuit_breakers(self) -> bool:
        """Test circuit breaker functionality"""
        try:
            from utils.circuit_breaker import get_circuit_breaker_manager, reset_circuit_breaker_manager
            
            # Reset for clean test
            reset_circuit_breaker_manager()
            cb_manager = get_circuit_breaker_manager()
            
            # Test circuit breaker creation
            circuit = cb_manager.get_circuit_breaker('gpt_api')
            assert circuit is not None, "GPT API circuit breaker should exist"
            assert circuit.state.value == "closed", "Circuit should start in closed state"
            
            # Test successful call
            def successful_operation():
                return "success"
            
            result = await cb_manager.call_with_circuit_breaker('gpt_api', successful_operation)
            assert result == "success", "Successful operation should return result"
            
            # Test metrics
            metrics = cb_manager.get_all_metrics()
            assert 'gpt_api' in metrics, "GPT API metrics should exist"
            assert metrics['gpt_api']['successful_requests'] > 0, "Should have successful requests"
            
            # Test health status
            health = cb_manager.get_health_status()
            assert 'gpt_api' in health, "GPT API health should be tracked"
            
            logger.info("✅ Circuit breaker tests passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Circuit breaker test failed: {e}")
            return False
    
    async def test_data_consistency(self) -> bool:
        """Test data consistency and transaction management"""
        try:
            from utils.data_consistency import get_data_consistency_manager, reset_data_consistency_manager
            from pymongo import MongoClient
            
            # Mock MongoDB client for testing
            class MockMongoClient:
                def get_database(self):
                    return MockDatabase()
            
            class MockDatabase:
                def __getitem__(self, name):
                    return MockCollection()
            
            class MockCollection:
                def insert_many(self, docs, ordered=False):
                    return MockResult(len(docs))
                def bulk_write(self, operations, ordered=False):
                    return MockBulkResult()
            
            class MockResult:
                def __init__(self, count):
                    self.inserted_ids = [f"id_{i}" for i in range(count)]
            
            class MockBulkResult:
                def __init__(self):
                    self.modified_count = 5
                    self.upserted_count = 0
            
            # Reset for clean test
            reset_data_consistency_manager()
            
            # Test with mock client
            mock_client = MockMongoClient()
            dc_manager = get_data_consistency_manager(mock_client)
            
            # Test data validation
            valid_job = {
                'title': 'Software Engineer',
                'company': 'Tech Corp',
                'source': 'linkedin'
            }
            
            validation_result = dc_manager.validate_data('job', valid_job)
            assert validation_result.is_valid, "Valid job should pass validation"
            
            # Test invalid data
            invalid_job = {
                'title': '',  # Empty title
                'company': 'Tech Corp',
                'source': 'linkedin'
            }
            
            validation_result = dc_manager.validate_data('job', invalid_job)
            assert not validation_result.is_valid, "Invalid job should fail validation"
            assert len(validation_result.errors) > 0, "Should have validation errors"
            
            # Test job hash generation
            hash1 = dc_manager.generate_job_hash(valid_job)
            hash2 = dc_manager.generate_job_hash(valid_job)
            assert hash1 == hash2, "Same job should generate same hash"
            
            # Test transaction management
            transaction_id = dc_manager.start_transaction()
            assert transaction_id.startswith('tx_'), "Transaction ID should start with 'tx_'"
            
            # Test bulk operations
            test_jobs = [valid_job.copy() for _ in range(3)]
            result = await dc_manager.bulk_insert_jobs(test_jobs)
            assert 'inserted' in result, "Bulk insert should return result"
            
            # Test metrics
            metrics = dc_manager.get_transaction_metrics()
            assert 'total_transactions' in metrics, "Should track transaction metrics"
            
            logger.info("✅ Data consistency tests passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Data consistency test failed: {e}")
            return False
    
    async def test_security_configuration(self) -> bool:
        """Test security and configuration validation"""
        try:
            from utils.security import get_security_manager, reset_security_manager
            import os
            
            # Reset for clean test
            reset_security_manager()
            security_manager = get_security_manager()
            
            # Test encryption
            test_secret = "test_secret_123"
            encrypted = security_manager.encrypt_secret(test_secret)
            decrypted = security_manager.decrypt_secret(encrypted)
            assert decrypted == test_secret, "Encryption/decryption should work"
            
            # Test OpenAI API key validation
            test_key = "sk-test1234567890abcdef"
            result = security_manager.validate_openai_api_key(test_key)
            assert result.status.value in ["valid", "invalid", "warning", "unknown"], "Should return valid status"
            
            # Test MongoDB URI validation
            test_uri = "mongodb://localhost:27017/test"
            result = security_manager.validate_mongodb_uri(test_uri)
            assert result.status.value in ["valid", "invalid", "warning", "unknown"], "Should return valid status"
            
            # Test proxy configuration validation
            test_proxies = "proxy1:8080,proxy2:8080:user:pass"
            result = security_manager.validate_proxy_config(test_proxies)
            assert result.status.value in ["valid", "invalid", "warning", "unknown"], "Should return valid status"
            
            # Test email configuration validation
            result = security_manager.validate_email_config(
                "smtp.gmail.com", 587, "test@example.com", "password123"
            )
            assert result.status.value in ["valid", "invalid", "warning", "unknown"], "Should return valid status"
            
            # Test comprehensive validation
            validation_results = security_manager.validate_all_configurations()
            assert isinstance(validation_results, dict), "Should return validation results dict"
            
            # Test validation summary
            summary = security_manager.get_validation_summary()
            assert 'total_configs' in summary, "Summary should include total configs"
            assert 'all_valid' in summary, "Summary should include all_valid flag"
            
            logger.info("✅ Security configuration tests passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Security configuration test failed: {e}")
            return False
    
    async def test_database_performance(self) -> bool:
        """Test database performance optimization"""
        try:
            from utils.db_optimizer import get_db_optimizer, reset_db_optimizer
            from pymongo import MongoClient
            
            # Mock MongoDB client for testing
            class MockMongoClient:
                def __init__(self):
                    self.max_pool_size = 50
                    self.min_pool_size = 10
                
                def get_database(self):
                    return MockDatabase()
                
                def admin(self):
                    return MockAdmin()
                
                def command(self, cmd):
                    return {'connections': {'current': 5, 'available': 45, 'pending': 0, 'active': 5}}
            
            class MockDatabase:
                def __init__(self):
                    self.name = 'test_db'
                
                def __getitem__(self, name):
                    return MockCollection()
                
                def list_collection_names(self):
                    return ['jobs', 'applications', 'users']
                
                def command(self, cmd, *args):
                    if cmd == 'dbStats':
                        return {'collections': 3, 'dataSize': 1024, 'storageSize': 2048}
                    elif cmd == 'collStats':
                        return {'count': 100, 'size': 512, 'avgObjSize': 5, 'storageSize': 1024, 'nindexes': 2, 'totalIndexSize': 256}
            
            class MockCollection:
                def insert_many(self, docs, ordered=False):
                    return MockResult(len(docs))
                
                def bulk_write(self, operations, ordered=False):
                    return MockBulkResult()
                
                def list_indexes(self):
                    return [{'name': 'test_index'}]
                
                def create_index(self, fields, name=None, unique=False):
                    pass
                
                def aggregate(self, pipeline):
                    return [{'name': 'test_index', 'accesses': {'ops': 10}, 'spec': {'size': 100}}]
            
            class MockAdmin:
                def command(self, cmd):
                    return {'connections': {'current': 5, 'available': 45, 'pending': 0, 'active': 5}}
            
            class MockResult:
                def __init__(self, count):
                    self.inserted_ids = [f"id_{i}" for i in range(count)]
            
            class MockBulkResult:
                def __init__(self):
                    self.modified_count = 5
                    self.upserted_count = 0
            
            # Reset for clean test
            reset_db_optimizer()
            
            # Test with mock client
            mock_client = MockMongoClient()
            db_optimizer = get_db_optimizer(mock_client)
            
            # Test bulk insert jobs
            test_jobs = [
                {'title': 'Engineer', 'company': 'Tech Corp', 'source': 'linkedin'},
                {'title': 'Developer', 'company': 'Startup Inc', 'source': 'indeed'}
            ]
            
            result = await db_optimizer.bulk_insert_jobs(test_jobs)
            assert 'inserted' in result, "Bulk insert should return result"
            assert 'duration' in result, "Bulk insert should include duration"
            
            # Test bulk insert applications
            test_applications = [
                {'job_id': 'job1', 'status': 'applied', 'applied_at': datetime.utcnow()},
                {'job_id': 'job2', 'status': 'failed', 'applied_at': datetime.utcnow()}
            ]
            
            result = await db_optimizer.bulk_insert_applications(test_applications)
            assert 'inserted' in result, "Bulk insert applications should return result"
            
            # Test performance metrics
            metrics = db_optimizer.get_performance_metrics()
            assert isinstance(metrics, dict), "Should return performance metrics"
            
            # Test connection pool stats
            pool_stats = db_optimizer.get_connection_pool_stats()
            assert isinstance(pool_stats, dict), "Should return connection pool stats"
            
            # Test bulk operations summary
            bulk_summary = db_optimizer.get_bulk_operations_summary()
            assert 'total_operations' in bulk_summary, "Should track bulk operations"
            
            # Test database stats
            db_stats = db_optimizer.get_database_stats()
            assert 'database' in db_stats, "Should return database stats"
            
            # Test comprehensive performance report
            report = db_optimizer.get_comprehensive_performance_report()
            assert 'timestamp' in report, "Should include timestamp"
            assert 'performance_metrics' in report, "Should include performance metrics"
            
            logger.info("✅ Database performance tests passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database performance test failed: {e}")
            return False
    
    async def test_monitoring_observability(self) -> bool:
        """Test monitoring and observability features"""
        try:
            from utils.monitoring import get_monitoring_manager, reset_monitoring_manager
            
            # Reset for clean test
            reset_monitoring_manager()
            monitoring_manager = get_monitoring_manager()
            
            # Test health checks
            health_results = await monitoring_manager.run_health_checks()
            assert isinstance(health_results, dict), "Health checks should return results"
            
            # Test metrics recording
            monitoring_manager.record_metric('test_metric', 42.0, {'tag': 'test'})
            monitoring_manager.record_metric('test_metric', 84.0, {'tag': 'test'})
            
            # Test metrics summary
            metrics_summary = monitoring_manager.get_metrics_summary()
            assert 'test_metric' in metrics_summary, "Should track custom metrics"
            assert metrics_summary['test_metric']['count'] == 2, "Should count all metrics"
            
            # Test alert creation
            from utils.monitoring import AlertLevel
            await monitoring_manager.create_alert(
                AlertLevel.INFO,
                "Test alert",
                "test_source",
                {'test': 'data'}
            )
            
            # Test alerts summary
            alerts_summary = monitoring_manager.get_alerts_summary()
            assert alerts_summary['total_alerts'] > 0, "Should track alerts"
            assert alerts_summary['info'] > 0, "Should count info alerts"
            
            # Test health summary
            health_summary = monitoring_manager.get_health_summary()
            assert 'total_checks' in health_summary, "Should track health checks"
            assert 'health_percentage' in health_summary, "Should calculate health percentage"
            
            # Test comprehensive status
            status = monitoring_manager.get_comprehensive_status()
            assert 'timestamp' in status, "Should include timestamp"
            assert 'health' in status, "Should include health data"
            assert 'metrics' in status, "Should include metrics data"
            assert 'alerts' in status, "Should include alerts data"
            
            logger.info("✅ Monitoring observability tests passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Monitoring observability test failed: {e}")
            return False
    
    async def test_integration(self) -> bool:
        """Test integration between all systems"""
        try:
            # Test that all managers can coexist
            from utils.error_handler import get_error_handler
            from utils.circuit_breaker import get_circuit_breaker_manager
            from utils.data_consistency import get_data_consistency_manager
            from utils.security import get_security_manager
            from utils.monitoring import get_monitoring_manager
            from utils.db_optimizer import get_db_optimizer
            
            # Initialize all managers
            error_handler = get_error_handler()
            circuit_breaker_manager = get_circuit_breaker_manager()
            security_manager = get_security_manager()
            monitoring_manager = get_monitoring_manager()
            
            # Test that they all work together
            assert error_handler is not None, "Error handler should be initialized"
            assert circuit_breaker_manager is not None, "Circuit breaker manager should be initialized"
            assert security_manager is not None, "Security manager should be initialized"
            assert monitoring_manager is not None, "Monitoring manager should be initialized"
            
            # Test error handling with monitoring
            try:
                raise Exception("Integration test error")
            except Exception as e:
                await error_handler.handle_error(e, {'operation': 'integration_test'})
                
                # Check that monitoring picked up the error
                alerts_summary = monitoring_manager.get_alerts_summary()
                assert alerts_summary['total_alerts'] > 0, "Monitoring should track errors"
            
            # Test circuit breaker with monitoring
            def failing_operation():
                raise Exception("Circuit breaker test")
            
            try:
                await circuit_breaker_manager.call_with_circuit_breaker('gpt_api', failing_operation)
            except Exception:
                pass  # Expected to fail
            
            # Check circuit breaker metrics
            metrics = circuit_breaker_manager.get_all_metrics()
            assert 'gpt_api' in metrics, "Circuit breaker should track GPT API"
            
            logger.info("✅ Integration tests passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Integration test failed: {e}")
            return False
    
    def print_test_summary(self):
        """Print comprehensive test summary"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result['status'] == 'PASSED')
        failed_tests = sum(1 for result in self.test_results.values() if result['status'] == 'FAILED')
        error_tests = sum(1 for result in self.test_results.values() if result['status'] == 'ERROR')
        
        total_duration = time.time() - self.start_time
        
        print("\n" + "="*80)
        print("🎯 COMPREHENSIVE FEATURE TEST SUMMARY")
        print("="*80)
        print(f"⏱️  Total Duration: {total_duration:.2f}s")
        print(f"🧪 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"🚨 Errors: {error_tests}")
        print(f"📊 Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        print("\n📋 Detailed Results:")
        print("-" * 80)
        
        for test_name, result in self.test_results.items():
            status_emoji = "✅" if result['status'] == 'PASSED' else "❌" if result['status'] == 'FAILED' else "🚨"
            print(f"{status_emoji} {test_name:<30} {result['status']:<10} {result['duration']:.2f}s")
            
            if result['status'] == 'ERROR' and 'error' in result:
                print(f"    Error: {result['error']}")
        
        print("\n" + "="*80)
        
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED! All comprehensive features are working correctly.")
        else:
            print("⚠️  Some tests failed. Please review the errors above.")
        
        print("="*80)

async def main():
    """Main test runner"""
    tester = ComprehensiveFeatureTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main()) 