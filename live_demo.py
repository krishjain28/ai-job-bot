#!/usr/bin/env python3
"""
Live Demo: AI Job Bot with Full Resilience Features
Shows rate limiting, caching, fallback, cost tracking, and API resilience in action.
"""

import logging
import time
import json
from datetime import datetime
from utils.gpt_manager import get_rate_limiter, reset_rate_limiter
from utils.cache import get_cache
from utils.api_resilience import get_api_manager, reset_api_manager
from utils.fallback_evaluator import get_fallback_evaluator
from gpt_filter import filter_jobs, generate_application_message

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def print_header(title):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f"🎯 {title}")
    print("="*60)

def print_section(title):
    """Print a formatted section"""
    print(f"\n📋 {title}")
    print("-" * 40)

def demo_rate_limiting():
    """Demo rate limiting and cost tracking"""
    print_header("DEMO 1: Rate Limiting & Cost Tracking")
    
    rate_limiter = get_rate_limiter()
    
    print_section("Initial State")
    stats = rate_limiter.get_stats()
    print(f"💰 Daily cost: ${stats['daily_cost']:.4f}")
    print(f"💰 Cost limit: ${stats['daily_cost_limit']:.2f}")
    print(f"💰 Cost remaining: ${stats['cost_remaining']:.4f}")
    print(f"📊 Daily requests: {stats['daily_requests']}")
    
    print_section("Simulating Multiple Requests")
    
    # Simulate some requests
    for i in range(3):
        estimated_cost = 0.002  # $0.002 per job evaluation
        can_proceed, reason = rate_limiter.can_make_request(estimated_cost)
        
        print(f"Request {i+1}: Can proceed = {can_proceed}, Reason = {reason}")
        
        if can_proceed:
            # Simulate a successful request
            rate_limiter.record_request(
                model="gpt-3.5-turbo",
                input_tokens=1000,
                output_tokens=500,
                cost=estimated_cost,
                success=True
            )
            print(f"  ✅ Recorded request {i+1} (${estimated_cost:.4f})")
        else:
            print(f"  ⏸️  Skipped request {i+1} due to rate limit")
    
    print_section("Updated State")
    stats = rate_limiter.get_stats()
    print(f"💰 Daily cost: ${stats['daily_cost']:.4f}")
    print(f"💰 Cost remaining: ${stats['cost_remaining']:.4f}")
    print(f"📊 Daily requests: {stats['daily_requests']}")

def demo_caching():
    """Demo Redis caching functionality"""
    print_header("DEMO 2: Redis Caching")
    
    cache = get_cache()
    
    # Sample job and resume
    job = {
        'title': 'Senior Python Developer',
        'company': 'TechCorp',
        'location': 'Remote',
        'tags': ['Python', 'Django', 'AWS', 'React'],
        'description': 'Looking for a senior Python developer with 5+ years of experience.'
    }
    
    resume_text = """
    Software Engineer with 6 years of experience in Python, Django, and AWS.
    Strong background in web development, API design, and cloud technologies.
    Experience with React, Docker, and microservices architecture.
    """
    
    print_section("Cache Key Generation")
    from utils.cache import job_eval_hash
    cache_key = job_eval_hash(job, resume_text)
    print(f"🔑 Cache key: {cache_key[:50]}...")
    
    print_section("Cache Operations")
    
    # Test cache miss
    cached_result = cache.get(cache_key)
    if cached_result is None:
        print("❌ Cache miss - no existing data")
    else:
        print("✅ Cache hit - found existing data")
    
    # Store some test data
    test_data = {
        'answer': 'Score: 8/10 - Excellent match for Python skills',
        'score': 8,
        'reason': 'Strong Python and Django experience alignment',
        'timestamp': datetime.now().isoformat()
    }
    
    print(f"💾 Storing data in cache (TTL: 24 hours)")
    cache.set(cache_key, test_data, ttl=24*60*60)
    
    # Retrieve the data
    retrieved_data = cache.get(cache_key)
    if retrieved_data == test_data:
        print("✅ Cache set/get working correctly")
    else:
        print("❌ Cache set/get failed")

def demo_fallback_evaluator():
    """Demo fallback job evaluator"""
    print_header("DEMO 3: Fallback Job Evaluator")
    
    evaluator = get_fallback_evaluator()
    
    # Test jobs with different skill matches
    test_jobs = [
        {
            'title': 'Senior Python Developer',
            'company': 'TechCorp',
            'tags': ['Python', 'Django', 'AWS'],
            'description': 'Looking for a senior Python developer with 5+ years of experience.'
        },
        {
            'title': 'Frontend Developer',
            'company': 'WebStartup',
            'tags': ['JavaScript', 'React', 'Node.js'],
            'description': 'Looking for a frontend developer with React experience.'
        },
        {
            'title': 'DevOps Engineer',
            'company': 'CloudTech',
            'tags': ['AWS', 'Docker', 'Kubernetes'],
            'description': 'Looking for a DevOps engineer with cloud experience.'
        }
    ]
    
    resume_text = """
    Software Engineer with 6 years of experience in Python, Django, and AWS.
    Strong background in web development, API design, and cloud technologies.
    Experience with React, Docker, and microservices architecture.
    """
    
    print_section("Job Evaluations")
    
    for i, job in enumerate(test_jobs, 1):
        score, reason = evaluator.evaluate_job(job, resume_text)
        print(f"Job {i}: {job['title']} at {job['company']}")
        print(f"  Score: {score}/10")
        print(f"  Reason: {reason}")
        print()

def demo_api_resilience():
    """Demo API resilience features"""
    print_header("DEMO 4: API Resilience")
    
    api_manager = get_api_manager()
    
    print_section("API Health Check")
    health = api_manager.health_check()
    print(f"Status: {health['status']}")
    if health['status'] == 'unhealthy':
        print(f"Error: {health['error'][:100]}...")
    
    print_section("Circuit Breaker Status")
    status = api_manager.get_status()
    cb_status = status['circuit_breaker']
    print(f"State: {cb_status['state']}")
    print(f"Failure count: {cb_status['failure_count']}")
    print(f"Last success: {cb_status['last_success_time']}")
    
    print_section("Fallback Models")
    fallback_models = status['fallback_models']
    print("Available fallback models:")
    for model in fallback_models:
        print(f"  - {model}")

def demo_integrated_job_filtering():
    """Demo integrated job filtering with all features"""
    print_header("DEMO 5: Integrated Job Filtering")
    
    # Sample jobs
    jobs = [
        {
            'title': 'Senior Python Developer',
            'company': 'TechCorp',
            'location': 'Remote',
            'salary': '$120k-150k',
            'tags': ['Python', 'Django', 'AWS', 'React'],
            'description': 'Looking for a senior Python developer with 5+ years of experience in Django and AWS.'
        },
        {
            'title': 'Frontend Developer',
            'company': 'WebStartup',
            'location': 'San Francisco',
            'salary': '$100k-130k',
            'tags': ['JavaScript', 'React', 'Node.js'],
            'description': 'Looking for a frontend developer with React experience.'
        },
        {
            'title': 'DevOps Engineer',
            'company': 'CloudTech',
            'location': 'Remote',
            'salary': '$130k-160k',
            'tags': ['AWS', 'Docker', 'Kubernetes', 'Python'],
            'description': 'Looking for a DevOps engineer with cloud and containerization experience.'
        },
        {
            'title': 'Data Scientist',
            'company': 'AITech',
            'location': 'New York',
            'salary': '$140k-180k',
            'tags': ['Python', 'Machine Learning', 'SQL', 'Statistics'],
            'description': 'Looking for a data scientist with ML experience.'
        }
    ]
    
    resume_text = """
    Software Engineer with 6 years of experience in Python, Django, and AWS.
    Strong background in web development, API design, and cloud technologies.
    Experience with React, Docker, and microservices architecture.
    Proficient in Python, JavaScript, AWS, Docker, and database technologies.
    """
    
    print_section("Starting Job Filtering")
    print(f"📋 Total jobs to evaluate: {len(jobs)}")
    print(f"📄 Resume length: {len(resume_text)} characters")
    
    # Get initial stats
    rate_limiter = get_rate_limiter()
    initial_stats = rate_limiter.get_stats()
    print(f"💰 Initial cost: ${initial_stats['daily_cost']:.4f}")
    
    print_section("Filtering Jobs (with all resilience features)")
    
    start_time = time.time()
    filtered_jobs = filter_jobs(jobs, resume_text)
    end_time = time.time()
    
    print_section("Results")
    print(f"⏱️  Processing time: {end_time - start_time:.2f} seconds")
    print(f"📋 Jobs evaluated: {len(jobs)}")
    print(f"🎯 Jobs filtered (score >= 7): {len(filtered_jobs)}")
    
    # Get final stats
    final_stats = rate_limiter.get_stats()
    cost_used = final_stats['daily_cost'] - initial_stats['daily_cost']
    print(f"💰 Cost used: ${cost_used:.4f}")
    print(f"💰 Total daily cost: ${final_stats['daily_cost']:.4f}")
    print(f"💰 Cost remaining: ${final_stats['cost_remaining']:.4f}")
    
    if filtered_jobs:
        print_section("Top Matching Jobs")
        for i, job in enumerate(filtered_jobs, 1):
            print(f"{i}. {job['title']} at {job['company']}")
            print(f"   Score: {job.get('gpt_score', 'N/A')}/10")
            print(f"   Reason: {job.get('gpt_reason', 'N/A')}")
            print()
    else:
        print("⚠️  No jobs met the minimum score threshold (7/10)")

def demo_cache_warming():
    """Demo cache warming functionality"""
    print_header("DEMO 6: Cache Warming")
    
    from utils.cache import warm_job_eval_cache
    
    # Sample common jobs
    common_jobs = [
        {
            'title': 'Software Engineer',
            'company': 'BigTech',
            'tags': ['Python', 'Java', 'AWS'],
            'description': 'General software engineering role.'
        },
        {
            'title': 'Full Stack Developer',
            'company': 'Startup',
            'tags': ['JavaScript', 'React', 'Node.js', 'Python'],
            'description': 'Full stack development role.'
        }
    ]
    
    resume_text = "Software engineer with Python and JavaScript experience."
    
    print_section("Warming Cache for Common Jobs")
    print(f"🔥 Warming cache for {len(common_jobs)} common jobs...")
    
    # Note: In a real scenario, you'd pass a GPT evaluation function
    # For demo, we'll just show the concept
    print("✅ Cache warming would pre-populate cache for frequently seen job patterns")
    print("✅ This reduces API calls and improves response times")

def main():
    """Run the complete live demo"""
    print_header("🤖 AI JOB BOT - LIVE DEMO")
    print("Demonstrating all resilience features: rate limiting, caching, fallback, and API resilience")
    
    try:
        # Reset all systems for clean demo
        print_section("Initializing Demo Environment")
        reset_rate_limiter()
        reset_api_manager()
        print("✅ All systems reset for clean demo")
        
        # Run all demos
        demo_rate_limiting()
        demo_caching()
        demo_fallback_evaluator()
        demo_api_resilience()
        demo_integrated_job_filtering()
        demo_cache_warming()
        
        print_header("🎉 DEMO COMPLETE")
        print("All resilience features demonstrated successfully!")
        print("\nKey Features Tested:")
        print("✅ Rate limiting and cost tracking")
        print("✅ Redis caching with TTL")
        print("✅ Fallback job evaluator")
        print("✅ API resilience and circuit breaker")
        print("✅ Integrated job filtering")
        print("✅ Cache warming concept")
        
    except Exception as e:
        print(f"❌ Demo error: {e}")
        logger.error(f"Demo failed: {e}")

if __name__ == "__main__":
    main() 