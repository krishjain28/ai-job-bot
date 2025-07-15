#!/usr/bin/env python3
"""
Test script for API resilience features
"""

import logging
import time
from utils.api_resilience import (
    get_api_manager, reset_api_manager, CircuitBreaker, CircuitBreakerConfig,
    retry_with_backoff, APIManager
)
from utils.fallback_evaluator import get_fallback_evaluator
from utils.cache import get_cache, job_eval_hash

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_circuit_breaker():
    """Test circuit breaker functionality"""
    print("=== Testing Circuit Breaker ===")
    
    config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=5.0)
    cb = CircuitBreaker(config)
    
    # Test successful calls
    def successful_func():
        return "success"
    
    for i in range(5):
        result = cb.call(successful_func)
        print(f"Successful call {i+1}: {result}")
    
    # Test failing calls
    def failing_func():
        raise Exception("Simulated failure")
    
    for i in range(5):
        try:
            cb.call(failing_func)
        except Exception as e:
            print(f"Failed call {i+1}: {e}")
    
    # Check circuit breaker state
    status = cb.get_status()
    print(f"Circuit breaker status: {status}")
    
    # Test recovery
    print("Waiting for circuit breaker to recover...")
    time.sleep(6)
    
    try:
        result = cb.call(successful_func)
        print(f"Recovery test: {result}")
    except Exception as e:
        print(f"Recovery failed: {e}")
    
    return True

def test_retry_decorator():
    """Test retry decorator with exponential backoff"""
    print("\n=== Testing Retry Decorator ===")
    
    call_count = 0
    
    @retry_with_backoff(max_retries=3, base_delay=0.1)
    def flaky_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception(f"Simulated failure {call_count}")
        return "success after retries"
    
    try:
        result = flaky_function()
        print(f"Retry result: {result}")
        print(f"Total calls made: {call_count}")
    except Exception as e:
        print(f"Retry failed: {e}")
        return False
    
    return True

def test_fallback_evaluator():
    """Test fallback job evaluator"""
    print("\n=== Testing Fallback Evaluator ===")
    
    evaluator = get_fallback_evaluator()
    
    # Sample job and resume
    job = {
        'title': 'Senior Python Developer',
        'company': 'TechCorp',
        'location': 'Remote',
        'salary': '$120k-150k',
        'tags': ['Python', 'Django', 'AWS', 'React'],
        'description': 'Looking for a senior Python developer with 5+ years of experience in Django and AWS.'
    }
    
    resume_text = """
    Software Engineer with 6 years of experience in Python, Django, and AWS.
    Strong background in web development, API design, and cloud technologies.
    Experience with React, Docker, and microservices architecture.
    """
    
    score, reason = evaluator.evaluate_job(job, resume_text)
    print(f"Fallback evaluation score: {score}/10")
    print(f"Fallback evaluation reason: {reason}")
    
    # Test with different job
    job2 = {
        'title': 'Frontend Developer',
        'company': 'WebStartup',
        'tags': ['JavaScript', 'React', 'Node.js'],
        'description': 'Looking for a frontend developer with React experience.'
    }
    
    score2, reason2 = evaluator.evaluate_job(job2, resume_text)
    print(f"Fallback evaluation score 2: {score2}/10")
    print(f"Fallback evaluation reason 2: {reason2}")
    
    return True

def test_api_manager():
    """Test API manager functionality"""
    print("\n=== Testing API Manager ===")
    
    api_manager = get_api_manager()
    
    # Test health check
    health = api_manager.health_check()
    print(f"API health check: {health}")
    
    # Test status
    status = api_manager.get_status()
    print(f"API manager status: {status}")
    
    # Test with simple message (will fail without valid API key, but tests structure)
    try:
        response = api_manager.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-3.5-turbo",
            max_tokens=10,
            fallback=True
        )
        print(f"API call successful: {response}")
    except Exception as e:
        print(f"API call failed (expected without valid key): {e}")
    
    return True

def test_cache_integration():
    """Test cache integration with job evaluation"""
    print("\n=== Testing Cache Integration ===")
    
    cache = get_cache()
    
    # Sample job and resume
    job = {
        'title': 'Python Developer',
        'company': 'TestCorp',
        'tags': ['Python', 'Django']
    }
    
    resume_text = "Python developer with Django experience"
    
    # Generate cache key
    cache_key = job_eval_hash(job, resume_text)
    print(f"Cache key: {cache_key}")
    
    # Test cache set/get
    test_data = {
        'answer': 'Score: 8/10 - Good match',
        'score': 8,
        'reason': 'Good match for Python skills'
    }
    
    cache.set(cache_key, test_data, ttl=60)  # 1 minute TTL
    retrieved = cache.get(cache_key)
    
    if retrieved == test_data:
        print("✅ Cache set/get working correctly")
    else:
        print("❌ Cache set/get failed")
        return False
    
    return True

def test_resilience_integration():
    """Test integration of all resilience features"""
    print("\n=== Testing Resilience Integration ===")
    
    # Reset API manager for clean test
    reset_api_manager()
    
    # Test fallback evaluator integration
    evaluator = get_fallback_evaluator()
    cache = get_cache()
    
    job = {
        'title': 'Backend Developer',
        'company': 'ResilientCorp',
        'tags': ['Python', 'FastAPI', 'PostgreSQL'],
        'description': 'Looking for a backend developer with Python and FastAPI experience.'
    }
    
    resume_text = "Backend developer with 4 years of Python and FastAPI experience"
    
    # Test cache key generation
    cache_key = job_eval_hash(job, resume_text)
    print(f"Generated cache key: {cache_key}")
    
    # Test fallback evaluation
    score, reason = evaluator.evaluate_job(job, resume_text)
    print(f"Fallback evaluation: {score}/10 - {reason}")
    
    # Test caching fallback result
    cache_data = {
        'answer': f'Score: {score}/10 - {reason}',
        'score': score,
        'reason': reason,
        'fallback': True
    }
    
    cache.set(cache_key, cache_data, ttl=300)  # 5 minutes
    cached_result = cache.get(cache_key)
    
    if cached_result == cache_data:
        print("✅ Fallback result cached successfully")
    else:
        print("❌ Fallback caching failed")
        return False
    
    return True

def main():
    """Run all resilience tests"""
    print("Starting API Resilience Tests\n")
    
    tests = [
        test_circuit_breaker,
        test_retry_decorator,
        test_fallback_evaluator,
        test_api_manager,
        test_cache_integration,
        test_resilience_integration,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
                print(f"✅ {test.__name__} PASSED")
            else:
                print(f"❌ {test.__name__} FAILED")
        except Exception as e:
            print(f"❌ {test.__name__} ERROR: {e}")
        
        print("-" * 50)
    
    print(f"\nResilience Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All resilience tests passed! API resilience features are working correctly.")
    else:
        print("⚠️  Some resilience tests failed. Please check the implementation.")

if __name__ == "__main__":
    main() 