import time
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class GPTRequest:
    """Represents a single GPT API request with cost tracking"""
    timestamp: float
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    success: bool
    error_message: Optional[str] = None

@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    daily_cost_limit: float = 2.0  # $2 per day
    max_concurrent_requests: int = 10

class GPTRateLimiter:
    """
    Manages GPT API rate limiting and cost control to prevent cost explosions.
    
    Features:
    - Rate limiting (requests per minute/hour)
    - Cost tracking and daily limits
    - Request history persistence
    - Automatic retry with exponential backoff
    - Cost estimation before requests
    """
    
    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self.request_history: List[GPTRequest] = []
        self.current_concurrent_requests = 0
        self.last_request_time = 0
        
        # Cost per 1K tokens for different models
        self.model_costs = {
            "gpt-4": {"input": 0.03, "output": 0.06},  # per 1K tokens
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004}
        }
        
        # Load existing request history
        self._load_history()
        
    def _get_history_file(self) -> Path:
        """Get the path to the request history file"""
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        return data_dir / "gpt_request_history.json"
    
    def _load_history(self):
        """Load request history from file"""
        history_file = self._get_history_file()
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    data = json.load(f)
                    self.request_history = [
                        GPTRequest(**req) for req in data.get('requests', [])
                    ]
                logger.info(f"Loaded {len(self.request_history)} historical requests")
            except Exception as e:
                logger.error(f"Failed to load request history: {e}")
                self.request_history = []
    
    def _save_history(self):
        """Save request history to file"""
        history_file = self._get_history_file()
        try:
            with open(history_file, 'w') as f:
                json.dump({
                    'requests': [asdict(req) for req in self.request_history],
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save request history: {e}")
    
    def _cleanup_old_requests(self, days: int = 7):
        """Remove requests older than specified days"""
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        self.request_history = [
            req for req in self.request_history 
            if req.timestamp > cutoff_time
        ]
    
    def estimate_cost(self, model: str, input_tokens: int, output_tokens: int = 0) -> float:
        """Estimate the cost of a GPT request"""
        if model not in self.model_costs:
            logger.warning(f"Unknown model {model}, using gpt-3.5-turbo pricing")
            model = "gpt-3.5-turbo"
        
        costs = self.model_costs[model]
        input_cost = (input_tokens / 1000) * costs["input"]
        output_cost = (output_tokens / 1000) * costs["output"]
        return input_cost + output_cost
    
    def get_daily_cost(self) -> float:
        """Calculate total cost for today"""
        today = datetime.now().date()
        daily_requests = [
            req for req in self.request_history
            if datetime.fromtimestamp(req.timestamp).date() == today
        ]
        return sum(req.cost for req in daily_requests)
    
    def get_requests_in_window(self, window_minutes: int) -> List[GPTRequest]:
        """Get requests within the specified time window"""
        cutoff_time = time.time() - (window_minutes * 60)
        return [
            req for req in self.request_history
            if req.timestamp > cutoff_time
        ]
    
    def can_make_request(self, estimated_cost: float = 0) -> Tuple[bool, str]:
        """
        Check if a request can be made based on rate limits and cost limits.
        Returns (can_proceed, reason)
        """
        now = time.time()
        
        # Check concurrent requests
        if self.current_concurrent_requests >= self.config.max_concurrent_requests:
            return False, "Too many concurrent requests"
        
        # Check requests per minute
        recent_requests = self.get_requests_in_window(1)
        if len(recent_requests) >= self.config.requests_per_minute:
            return False, "Rate limit exceeded (requests per minute)"
        
        # Check requests per hour
        hourly_requests = self.get_requests_in_window(60)
        if len(hourly_requests) >= self.config.requests_per_hour:
            return False, "Rate limit exceeded (requests per hour)"
        
        # Check daily cost limit
        daily_cost = self.get_daily_cost()
        if daily_cost + estimated_cost > self.config.daily_cost_limit:
            return False, f"Daily cost limit exceeded (${daily_cost:.2f} + ${estimated_cost:.2f} > ${self.config.daily_cost_limit})"
        
        # Check minimum time between requests (rate limiting)
        if now - self.last_request_time < (60 / self.config.requests_per_minute):
            return False, "Request too soon after last request"
        
        return True, "OK"
    
    def wait_if_needed(self, estimated_cost: float = 0) -> float:
        """
        Wait if necessary to respect rate limits.
        Returns the wait time in seconds.
        """
        wait_time = 0
        
        while True:
            can_proceed, reason = self.can_make_request(estimated_cost)
            if can_proceed:
                break
            
            if "requests per minute" in reason:
                # Wait for next minute window
                wait_time = 60 - (time.time() % 60)
            elif "requests per hour" in reason:
                # Wait for next hour window
                wait_time = 3600 - (time.time() % 3600)
            elif "concurrent" in reason:
                # Wait a bit for concurrent requests to finish
                wait_time = 1
            elif "cost limit" in reason:
                # Can't proceed today, wait until tomorrow
                tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                wait_time = (tomorrow - datetime.now()).total_seconds()
            else:
                # Default wait
                wait_time = 1
            
            logger.warning(f"Rate limit hit: {reason}. Waiting {wait_time:.1f} seconds")
            time.sleep(min(wait_time, 60))  # Sleep in chunks of max 60 seconds
        
        return wait_time
    
    def record_request(self, model: str, input_tokens: int, output_tokens: int, 
                      cost: float, success: bool, error_message: str = None):
        """Record a completed GPT request"""
        request = GPTRequest(
            timestamp=time.time(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            success=success,
            error_message=error_message
        )
        
        self.request_history.append(request)
        self.last_request_time = request.timestamp
        
        # Cleanup old requests periodically
        if len(self.request_history) % 100 == 0:
            self._cleanup_old_requests()
        
        # Save history periodically
        if len(self.request_history) % 10 == 0:
            self._save_history()
        
        logger.info(f"Recorded GPT request: {model}, cost: ${cost:.4f}, success: {success}")
    
    def get_stats(self) -> Dict:
        """Get current rate limiting statistics"""
        now = time.time()
        today = datetime.now().date()
        
        # Daily stats
        daily_requests = [
            req for req in self.request_history
            if datetime.fromtimestamp(req.timestamp).date() == today
        ]
        daily_cost = sum(req.cost for req in daily_requests)
        daily_success_rate = (
            len([req for req in daily_requests if req.success]) / len(daily_requests)
            if daily_requests else 0
        )
        
        # Recent stats (last hour)
        recent_requests = self.get_requests_in_window(60)
        recent_cost = sum(req.cost for req in recent_requests)
        
        return {
            "daily_requests": len(daily_requests),
            "daily_cost": daily_cost,
            "daily_cost_limit": self.config.daily_cost_limit,
            "daily_success_rate": daily_success_rate,
            "recent_requests_1h": len(recent_requests),
            "recent_cost_1h": recent_cost,
            "current_concurrent": self.current_concurrent_requests,
            "total_requests": len(self.request_history),
            "cost_remaining": max(0, self.config.daily_cost_limit - daily_cost)
        }
    
    def __enter__(self):
        """Context manager entry"""
        self.current_concurrent_requests += 1
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.current_concurrent_requests = max(0, self.current_concurrent_requests - 1)

# Global rate limiter instance
_rate_limiter: Optional[GPTRateLimiter] = None

def get_rate_limiter() -> GPTRateLimiter:
    """Get the global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = GPTRateLimiter()
    return _rate_limiter

def reset_rate_limiter():
    """Reset the global rate limiter (useful for testing)"""
    global _rate_limiter
    _rate_limiter = None 