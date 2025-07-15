import redis
import hashlib
import json
import logging
import os

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)

# Default TTL for job evaluations (in seconds)
DEFAULT_JOB_TTL = 24 * 60 * 60  # 24 hours

logger = logging.getLogger(__name__)

class RedisCache:
    def __init__(self, host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD):
        self.client = redis.Redis(host=host, port=port, db=db, password=password, decode_responses=True)

    def get(self, key):
        try:
            value = self.client.get(key)
            if value is not None:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    def set(self, key, value, ttl=DEFAULT_JOB_TTL):
        try:
            self.client.set(key, json.dumps(value), ex=ttl)
        except Exception as e:
            logger.error(f"Redis set error: {e}")

    def exists(self, key):
        try:
            return self.client.exists(key)
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False

    def delete(self, key):
        try:
            self.client.delete(key)
        except Exception as e:
            logger.error(f"Redis delete error: {e}")

    def keys(self, pattern='*'):
        try:
            return self.client.keys(pattern)
        except Exception as e:
            logger.error(f"Redis keys error: {e}")
            return []

# Helper to create a hash for job+resume
def job_eval_hash(job: dict, resume_text: str) -> str:
    job_str = json.dumps(job, sort_keys=True)
    resume_hash = hashlib.sha256(resume_text.encode('utf-8')).hexdigest()
    job_hash = hashlib.sha256(job_str.encode('utf-8')).hexdigest()
    return f"gpt_eval:{job_hash}:{resume_hash}"

# Singleton cache instance
_cache = None

def get_cache():
    global _cache
    if _cache is None:
        _cache = RedisCache()
    return _cache

def warm_job_eval_cache(jobs: list, resume_text: str, gpt_eval_func, ttl=DEFAULT_JOB_TTL):
    """
    Pre-populate the cache for a list of jobs and a resume using the provided GPT evaluation function.
    Only populates if not already cached.
    """
    cache = get_cache()
    for job in jobs:
        key = job_eval_hash(job, resume_text)
        if not cache.exists(key):
            logger.info(f"Warming cache for job {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}")
            result = gpt_eval_func(job, resume_text)
            if result:
                cache.set(key, result, ttl=ttl) 