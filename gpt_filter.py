from typing import List, Dict
import logging
import tiktoken
from config import OPENAI_API_KEY
from utils.gpt_manager import get_rate_limiter
from utils.cache import get_cache, job_eval_hash, DEFAULT_JOB_TTL
from utils.api_resilience import get_api_manager
from utils.fallback_evaluator import get_fallback_evaluator

logger = logging.getLogger(__name__)

# Get resilient API manager
api_manager = get_api_manager()

# Initialize tokenizer for cost estimation
try:
    tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
except:
    tokenizer = None

def filter_jobs(jobs: List[Dict], resume_text: str) -> List[Dict]:
    """Filter jobs using GPT based on resume match with rate limiting and Redis caching"""
    filtered = []
    rate_limiter = get_rate_limiter()
    cache = get_cache()
    
    if not resume_text:
        logger.warning("No resume text provided for filtering")
        return jobs
    
    for job in jobs:
        try:
            # Create a comprehensive prompt for job matching
            prompt = f"""
            Resume Summary:
            {resume_text[:2000]}...

            Job Details:
            - Title: {job['title']}
            - Company: {job['company']}
            - Location: {job.get('location', 'Remote')}
            - Salary: {job.get('salary', 'Not specified')}
            - Tags: {', '.join(job.get('tags', []))}

            Based on the resume and job details above, rate this job match from 1-10 and provide a brief explanation.
            Consider:
            1. Skills alignment
            2. Experience level match
            3. Company size/type fit
            4. Location preferences

            Format your response as: "Score: X/10 - [brief explanation]"
            """
            
            # Cache key for this job+resume
            cache_key = job_eval_hash(job, resume_text)
            cached = cache.get(cache_key)
            if cached:
                logger.info(f"Cache hit for job {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}")
                answer = cached['answer']
                score = cached['score']
                if score >= 7:
                    job['gpt_score'] = score
                    job['gpt_reason'] = cached.get('reason', answer)
                    filtered.append(job)
                continue
            
            # Estimate cost before making request
            model = "gpt-3.5-turbo"
            input_tokens = len(tokenizer.encode(prompt)) if tokenizer else len(prompt.split())
            estimated_cost = rate_limiter.estimate_cost(model, input_tokens, 150)
            
            # Check rate limits and wait if needed
            can_proceed, reason = rate_limiter.can_make_request(estimated_cost)
            if not can_proceed:
                logger.warning(f"Skipping job {job.get('title', 'Unknown')} due to rate limit: {reason}")
                continue
            
            # Wait if needed to respect rate limits
            wait_time = rate_limiter.wait_if_needed(estimated_cost)
            if wait_time > 0:
                logger.info(f"Waited {wait_time:.1f} seconds for rate limiting")
            
            # Try GPT API first, fallback to keyword matching if all fails
            gpt_success = False
            try:
                # Make the API request with rate limiter context and resilience
                with rate_limiter:
                    response = api_manager.chat_completion(
                        messages=[{"role": "user", "content": prompt}],
                        model=model,
                        max_tokens=150,
                        temperature=0.3,
                        fallback=True
                    )
                    
                    # Record the request for cost tracking
                    output_tokens = response.usage.completion_tokens
                    input_tokens_actual = response.usage.prompt_tokens
                    actual_cost = rate_limiter.estimate_cost(model, input_tokens_actual, output_tokens)
                    
                    rate_limiter.record_request(
                        model=model,
                        input_tokens=input_tokens_actual,
                        output_tokens=output_tokens,
                        cost=actual_cost,
                        success=True
                    )
                    
                    answer = response.choices[0].message.content.strip()
                    gpt_success = True
                    
            except Exception as e:
                logger.error(f"All GPT API calls failed for job {job.get('title', 'Unknown')}: {e}")
                # Record failed request
                rate_limiter.record_request(
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=0,
                    cost=0,
                    success=False,
                    error_message=str(e)
                )
                
                # Use fallback evaluator
                logger.info(f"Using fallback evaluator for job {job.get('title', 'Unknown')}")
                fallback_evaluator = get_fallback_evaluator()
                score, reason = fallback_evaluator.evaluate_job(job, resume_text)
                
                if score >= 7:
                    job['gpt_score'] = score
                    job['gpt_reason'] = f"Fallback evaluation: {reason}"
                    filtered.append(job)
                
                # Cache the fallback result
                cache.set(cache_key, {
                    'answer': f"Score: {score}/10 - {reason}",
                    'score': score,
                    'reason': reason,
                    'fallback': True
                }, ttl=DEFAULT_JOB_TTL)
                
                continue
                
            # Process GPT response if successful
            if gpt_success:
                # Extract score from response
                if "Score:" in answer:
                    score_text = answer.split("Score:")[1].split("-")[0].strip()
                    try:
                        score = int(score_text.split("/")[0])
                        if score >= 7:  # Only include high-matching jobs
                            job['gpt_score'] = score
                            job['gpt_reason'] = answer.split("-", 1)[1].strip() if "-" in answer else ""
                            filtered.append(job)
                        # Cache the result
                        cache.set(cache_key, {
                            'answer': answer,
                            'score': score,
                            'reason': answer.split("-", 1)[1].strip() if "-" in answer else ""
                        }, ttl=DEFAULT_JOB_TTL)
                    except ValueError:
                        logger.warning(f"Could not parse GPT score: {score_text}")
                        # Cache the raw answer for debugging
                        cache.set(cache_key, {'answer': answer, 'score': None, 'reason': answer}, ttl=DEFAULT_JOB_TTL)
                else:
                    # Cache the raw answer for debugging
                    cache.set(cache_key, {'answer': answer, 'score': None, 'reason': answer}, ttl=DEFAULT_JOB_TTL)
                        
        except Exception as e:
            logger.error(f"Error filtering job {job.get('title', 'Unknown')}: {e}")
            # Record failed request
            rate_limiter.record_request(
                model=model,
                input_tokens=input_tokens,
                output_tokens=0,
                cost=0,
                success=False,
                error_message=str(e)
            )
            continue
            
    # Sort by GPT score
    filtered.sort(key=lambda x: x.get('gpt_score', 0), reverse=True)
    
    return filtered

def generate_application_message(job: Dict, resume_text: str) -> str:
    """Generate a personalized application message using GPT with rate limiting"""
    rate_limiter = get_rate_limiter()
    
    try:
        prompt = f"""
        Resume:
        {resume_text[:1500]}...

        Job: {job['title']} at {job['company']}
        
        Generate a brief, professional application message (2-3 sentences) that:
        1. Shows enthusiasm for the role
        2. Mentions relevant experience from the resume
        3. Is personalized to the specific job/company
        4. Maintains a professional but friendly tone
        
        Keep it concise and natural.
        """
        
        # Estimate cost before making request
        model = "gpt-3.5-turbo"
        input_tokens = len(tokenizer.encode(prompt)) if tokenizer else len(prompt.split())
        estimated_cost = rate_limiter.estimate_cost(model, input_tokens, 200)
        
        # Check rate limits and wait if needed
        can_proceed, reason = rate_limiter.can_make_request(estimated_cost)
        if not can_proceed:
            logger.warning(f"Cannot generate application message due to rate limit: {reason}")
            return f"I'm excited to apply for the {job['title']} position at {job['company']}. I believe my experience aligns well with your requirements."
        
        # Wait if needed to respect rate limits
        wait_time = rate_limiter.wait_if_needed(estimated_cost)
        if wait_time > 0:
            logger.info(f"Waited {wait_time:.1f} seconds for rate limiting")
        
        # Make the API request with rate limiter context and resilience
        with rate_limiter:
            try:
                response = api_manager.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    model=model,
                    max_tokens=200,
                    temperature=0.7,
                    fallback=True
                )
                
                # Record the request for cost tracking
                output_tokens = response.usage.completion_tokens
                input_tokens_actual = response.usage.prompt_tokens
                actual_cost = rate_limiter.estimate_cost(model, input_tokens_actual, output_tokens)
                
                rate_limiter.record_request(
                    model=model,
                    input_tokens=input_tokens_actual,
                    output_tokens=output_tokens,
                    cost=actual_cost,
                    success=True
                )
                
                return response.choices[0].message.content.strip()
                
            except Exception as e:
                logger.error(f"API call failed for application message: {e}")
                # Record failed request
                rate_limiter.record_request(
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=0,
                    cost=0,
                    success=False,
                    error_message=str(e)
                )
                return f"I'm excited to apply for the {job['title']} position at {job['company']}. I believe my experience aligns well with your requirements."
        
    except Exception as e:
        logger.error(f"Error generating application message: {e}")
        # Record failed request
        rate_limiter.record_request(
            model=model,
            input_tokens=input_tokens,
            output_tokens=0,
            cost=0,
            success=False,
            error_message=str(e)
        )
        return f"I'm excited to apply for the {job['title']} position at {job['company']}. I believe my experience aligns well with your requirements." 