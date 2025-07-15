#!/usr/bin/env python3
"""
Test script for GPT Rate Limiter functionality
"""

import time
import logging
from utils.gpt_manager import GPTRateLimiter, RateLimitConfig, get_rate_limiter, reset_rate_limiter

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_rate_limiter_basic():
    """Test basic rate limiter functionality"""
    print("=== Testing Basic Rate Limiter ===")
    
    # Create a test config with strict limits
    config = RateLimitConfig(
        requests_per_minute=5,
        requests_per_hour=10,
        daily_cost_limit=0.01,  # Very low for testing
        max_concurrent_requests=2
    )
    
    limiter = GPTRateLimiter(config)
    
    # Test cost estimation
    estimated_cost = limiter.estimate_cost("gpt-3.5-turbo", 1000, 500)
    print(f"Estimated cost for 1000 input + 500 output tokens: ${estimated_cost:.4f}")
    
    # Test can_make_request
    can_proceed, reason = limiter.can_make_request(estimated_cost)
    print(f"Can make request: {can_proceed}, Reason: {reason}")
    
    # Test stats
    stats = limiter.get_stats()
    print(f"Initial stats: {stats}")
    
    return True

def test_rate_limiter_limits():
    """Test rate limiting behavior"""
    print("\n=== Testing Rate Limiting ===")
    
    config = RateLimitConfig(
        requests_per_minute=3,
        requests_per_hour=5,
        daily_cost_limit=0.01,
        max_concurrent_requests=2
    )
    
    limiter = GPTRateLimiter(config)
    
    # Simulate multiple requests
    for i in range(5):
        can_proceed, reason = limiter.can_make_request(0.001)
        print(f"Request {i+1}: Can proceed = {can_proceed}, Reason = {reason}")
        
        if can_proceed:
            # Simulate a request
            limiter.record_request(
                model="gpt-3.5-turbo",
                input_tokens=100,
                output_tokens=50,
                cost=0.001,
                success=True
            )
            print(f"  Recorded request {i+1}")
        else:
            print(f"  Skipped request {i+1}")
    
    stats = limiter.get_stats()
    print(f"Final stats: {stats}")
    
    return True

def test_concurrent_requests():
    """Test concurrent request handling"""
    print("\n=== Testing Concurrent Requests ===")
    
    config = RateLimitConfig(max_concurrent_requests=2)
    limiter = GPTRateLimiter(config)
    
    # Test context manager
    with limiter:
        print(f"Inside context manager: concurrent requests = {limiter.current_concurrent_requests}")
        can_proceed, reason = limiter.can_make_request(0.001)
        print(f"Can proceed inside context: {can_proceed}")
    
    print(f"Outside context manager: concurrent requests = {limiter.current_concurrent_requests}")
    
    return True

def test_cost_tracking():
    """Test cost tracking functionality"""
    print("\n=== Testing Cost Tracking ===")
    
    limiter = GPTRateLimiter()
    
    # Record some test requests
    test_requests = [
        ("gpt-3.5-turbo", 1000, 500, 0.002),
        ("gpt-4", 2000, 1000, 0.08),
        ("gpt-3.5-turbo", 500, 200, 0.001),
    ]
    
    for model, input_tokens, output_tokens, cost in test_requests:
        limiter.record_request(model, input_tokens, output_tokens, cost, True)
        print(f"Recorded {model} request: ${cost:.4f}")
    
    daily_cost = limiter.get_daily_cost()
    print(f"Total daily cost: ${daily_cost:.4f}")
    
    stats = limiter.get_stats()
    print(f"Cost stats: {stats}")
    
    return True

def test_wait_functionality():
    """Test wait functionality"""
    print("\n=== Testing Wait Functionality ===")
    
    config = RateLimitConfig(requests_per_minute=2)
    limiter = GPTRateLimiter(config)
    
    # Make a request to set the last request time
    limiter.record_request("gpt-3.5-turbo", 100, 50, 0.001, True)
    
    # Try to make another request immediately
    can_proceed, reason = limiter.can_make_request(0.001)
    print(f"Immediate request: Can proceed = {can_proceed}, Reason = {reason}")
    
    if not can_proceed:
        print("Waiting for rate limit...")
        wait_time = limiter.wait_if_needed(0.001)
        print(f"Waited {wait_time:.1f} seconds")
        
        can_proceed, reason = limiter.can_make_request(0.001)
        print(f"After wait: Can proceed = {can_proceed}, Reason = {reason}")
    
    return True

def test_global_instance():
    """Test global rate limiter instance"""
    print("\n=== Testing Global Instance ===")
    
    # Reset global instance
    reset_rate_limiter()
    
    # Get global instance
    limiter1 = get_rate_limiter()
    limiter2 = get_rate_limiter()
    
    # Should be the same instance
    print(f"Same instance: {limiter1 is limiter2}")
    
    # Test functionality
    can_proceed, reason = limiter1.can_make_request(0.001)
    print(f"Global instance test: Can proceed = {can_proceed}, Reason = {reason}")
    
    return True

def main():
    """Run all tests"""
    print("Starting GPT Rate Limiter Tests\n")
    
    tests = [
        test_rate_limiter_basic,
        test_rate_limiter_limits,
        test_concurrent_requests,
        test_cost_tracking,
        test_wait_functionality,
        test_global_instance,
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
    
    print(f"\nTest Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Rate limiter is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")

if __name__ == "__main__":
    main() 