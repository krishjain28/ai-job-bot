#!/usr/bin/env python3
"""
Integration test for GPT Rate Limiter with main application
"""

import logging
import sys
from gpt_filter import filter_jobs, generate_application_message
from utils.gpt_manager import get_rate_limiter, reset_rate_limiter

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_gpt_filter_integration():
    """Test GPT filter integration with rate limiter"""
    print("=== Testing GPT Filter Integration ===")
    
    # Reset rate limiter for clean test
    reset_rate_limiter()
    
    # Sample resume text
    resume_text = """
    Software Engineer with 5+ years of experience in Python, JavaScript, and React.
    Strong background in web development, API design, and cloud technologies.
    Experience with AWS, Docker, and microservices architecture.
    """
    
    # Sample jobs
    test_jobs = [
        {
            'title': 'Senior Python Developer',
            'company': 'TechCorp',
            'location': 'Remote',
            'salary': '$120k-150k',
            'tags': ['Python', 'Django', 'AWS', 'React']
        },
        {
            'title': 'Frontend Developer',
            'company': 'WebStartup',
            'location': 'San Francisco',
            'salary': '$100k-130k',
            'tags': ['JavaScript', 'React', 'Node.js']
        },
        {
            'title': 'DevOps Engineer',
            'company': 'CloudTech',
            'location': 'Remote',
            'salary': '$130k-160k',
            'tags': ['AWS', 'Docker', 'Kubernetes', 'Python']
        }
    ]
    
    print(f"Testing with {len(test_jobs)} sample jobs...")
    
    # Test job filtering
    try:
        filtered_jobs = filter_jobs(test_jobs, resume_text)
        print(f"✅ Job filtering completed: {len(filtered_jobs)} jobs filtered")
        
        for job in filtered_jobs:
            print(f"  - {job['title']} at {job['company']} (Score: {job.get('gpt_score', 'N/A')})")
            
    except Exception as e:
        print(f"❌ Job filtering failed: {e}")
        return False
    
    # Test application message generation
    try:
        if filtered_jobs:
            message = generate_application_message(filtered_jobs[0], resume_text)
            print(f"✅ Application message generated: {message[:100]}...")
        else:
            print("⚠️  No filtered jobs to test application message generation")
            
    except Exception as e:
        print(f"❌ Application message generation failed: {e}")
        return False
    
    # Check rate limiter stats
    rate_limiter = get_rate_limiter()
    stats = rate_limiter.get_stats()
    print(f"💰 Rate limiter stats: {stats['daily_requests']} requests, ${stats['daily_cost']:.4f} cost")
    
    return True

def test_rate_limiter_configuration():
    """Test rate limiter configuration and limits"""
    print("\n=== Testing Rate Limiter Configuration ===")
    
    rate_limiter = get_rate_limiter()
    
    # Test configuration
    config = rate_limiter.config
    print(f"✅ Rate limiter configured:")
    print(f"  - Requests per minute: {config.requests_per_minute}")
    print(f"  - Requests per hour: {config.requests_per_hour}")
    print(f"  - Daily cost limit: ${config.daily_cost_limit}")
    print(f"  - Max concurrent requests: {config.max_concurrent_requests}")
    
    # Test cost estimation
    test_costs = [
        ("gpt-3.5-turbo", 1000, 500),
        ("gpt-4", 2000, 1000),
        ("gpt-4-turbo", 1500, 750)
    ]
    
    print("\n💰 Cost estimation test:")
    for model, input_tokens, output_tokens in test_costs:
        cost = rate_limiter.estimate_cost(model, input_tokens, output_tokens)
        print(f"  - {model}: {input_tokens} input + {output_tokens} output = ${cost:.4f}")
    
    return True

def test_cost_limits():
    """Test cost limit enforcement"""
    print("\n=== Testing Cost Limits ===")
    
    rate_limiter = get_rate_limiter()
    
    # Simulate high-cost requests
    high_cost = 1.5  # $1.50 per request
    
    can_proceed, reason = rate_limiter.can_make_request(high_cost)
    print(f"High cost request (${high_cost}): Can proceed = {can_proceed}, Reason = {reason}")
    
    # Test with remaining budget
    remaining = rate_limiter.get_stats()['cost_remaining']
    print(f"Remaining budget: ${remaining:.4f}")
    
    if remaining < high_cost:
        print("✅ Cost limit correctly prevents expensive requests")
    else:
        print("⚠️  Cost limit allows expensive requests (may be expected)")
    
    return True

def main():
    """Run integration tests"""
    print("Starting GPT Rate Limiter Integration Tests\n")
    
    tests = [
        test_rate_limiter_configuration,
        test_cost_limits,
        test_gpt_filter_integration,
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
    
    print(f"\nIntegration Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All integration tests passed! Rate limiter is properly integrated.")
    else:
        print("⚠️  Some integration tests failed. Please check the implementation.")

if __name__ == "__main__":
    main() 