import time
import logging
import functools
from typing import Callable, Any, Optional, Dict, List
from enum import Enum
import asyncio
from dataclasses import dataclass
from openai import OpenAI, RateLimitError, APIError, APITimeoutError, APIConnectionError
from config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service is back

@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    expected_exception: type = Exception
    monitor_interval: float = 10.0

class CircuitBreaker:
    """Circuit breaker pattern implementation for API resilience"""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self.last_success_time = 0
        
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.config.recovery_timeout:
                logger.info("Circuit breaker transitioning to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN - service unavailable")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.config.expected_exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        self.last_success_time = time.time()
        if self.state == CircuitState.HALF_OPEN:
            logger.info("Circuit breaker transitioning to CLOSED")
            self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.config.failure_threshold:
            logger.warning(f"Circuit breaker opening after {self.failure_count} failures")
            self.state = CircuitState.OPEN
    
    def get_status(self) -> Dict:
        """Get current circuit breaker status"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "last_success_time": self.last_success_time
        }

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: tuple = (RateLimitError, APIError, APITimeoutError, APIConnectionError)
):
    """Decorator for retrying API calls with exponential backoff"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}: {e}")
                        raise e
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base ** attempt), max_delay)
                    
                    # Add jitter to prevent thundering herd
                    if jitter:
                        delay *= (0.5 + 0.5 * time.time() % 1)
                    
                    logger.warning(f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                                 f"Retrying in {delay:.2f}s...")
                    
                    time.sleep(delay)
            
            raise last_exception
        return wrapper
    return decorator

class APIManager:
    """Manages OpenAI API calls with resilience features"""
    
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY, timeout=30.0)
        self.circuit_breaker = CircuitBreaker(CircuitBreakerConfig())
        self.request_queue = []
        self.fallback_models = ["gpt-3.5-turbo", "gpt-3.5-turbo-16k", "gpt-4-turbo"]
        
    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=60.0)
    def chat_completion(self, messages: List[Dict], model: str = "gpt-3.5-turbo", 
                       max_tokens: int = 150, temperature: float = 0.3, 
                       fallback: bool = True) -> Dict:
        """Make chat completion with resilience and fallback"""
        
        def _make_request(model_name: str):
            return self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
        
        # Try with circuit breaker protection
        try:
            return self.circuit_breaker.call(_make_request, model)
        except RateLimitError as e:
            logger.warning(f"Rate limit hit for model {model}: {e}")
            if fallback:
                return self._try_fallback_models(messages, max_tokens, temperature)
            raise e
        except Exception as e:
            logger.error(f"API call failed for model {model}: {e}")
            if fallback:
                return self._try_fallback_models(messages, max_tokens, temperature)
            raise e
    
    def _try_fallback_models(self, messages: List[Dict], max_tokens: int, temperature: float) -> Dict:
        """Try fallback models if primary model fails"""
        for fallback_model in self.fallback_models:
            try:
                logger.info(f"Trying fallback model: {fallback_model}")
                return self.client.chat.completions.create(
                    model=fallback_model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
            except Exception as e:
                logger.warning(f"Fallback model {fallback_model} also failed: {e}")
                continue
        
        raise Exception("All models failed, including fallbacks")
    
    def health_check(self) -> Dict:
        """Perform health check on OpenAI API"""
        try:
            # Simple health check with minimal tokens
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1
            )
            return {
                "status": "healthy",
                "response_time": "ok",
                "model": "gpt-3.5-turbo"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "circuit_breaker": self.circuit_breaker.get_status()
            }
    
    def get_status(self) -> Dict:
        """Get comprehensive API status"""
        return {
            "circuit_breaker": self.circuit_breaker.get_status(),
            "health": self.health_check(),
            "fallback_models": self.fallback_models
        }

# Global API manager instance
_api_manager: Optional[APIManager] = None

def get_api_manager() -> APIManager:
    """Get global API manager instance"""
    global _api_manager
    if _api_manager is None:
        _api_manager = APIManager()
    return _api_manager

def reset_api_manager():
    """Reset global API manager (useful for testing)"""
    global _api_manager
    _api_manager = None 