import logging
import time
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service is back

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5      # Number of failures to open circuit
    recovery_timeout: float = 60.0  # Time to wait before trying half-open
    expected_exception: type = Exception  # Exception type to count as failure
    success_threshold: int = 2      # Number of successes to close circuit
    timeout: float = 30.0           # Timeout for operations

@dataclass
class CircuitBreakerMetrics:
    """Circuit breaker metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    circuit_opens: int = 0
    circuit_closes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    current_failure_count: int = 0
    current_success_count: int = 0

class CircuitBreaker:
    """Circuit breaker implementation"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.metrics = CircuitBreakerMetrics()
        self.last_state_change = time.time()
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        
        async with self._lock:
            # Check if circuit is open
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_state_change > self.config.recovery_timeout:
                    logger.info(f"Circuit {self.name}: Attempting to close circuit")
                    self.state = CircuitState.HALF_OPEN
                    self.last_state_change = time.time()
                else:
                    raise Exception(f"Circuit {self.name} is OPEN - failing fast")
            
            # Execute the function
            try:
                start_time = time.time()
                
                if asyncio.iscoroutinefunction(func):
                    result = await asyncio.wait_for(func(*args, **kwargs), timeout=self.config.timeout)
                else:
                    # Run sync function in thread pool
                    loop = asyncio.get_event_loop()
                    result = await asyncio.wait_for(
                        loop.run_in_executor(None, func, *args, **kwargs),
                        timeout=self.config.timeout
                    )
                
                # Success
                await self._on_success()
                return result
                
            except asyncio.TimeoutError:
                await self._on_failure(Exception(f"Operation timed out after {self.config.timeout}s"))
                raise
            except Exception as e:
                await self._on_failure(e)
                raise
    
    async def _on_success(self):
        """Handle successful operation"""
        self.metrics.total_requests += 1
        self.metrics.successful_requests += 1
        self.metrics.last_success_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            self.metrics.current_success_count += 1
            
            if self.metrics.current_success_count >= self.config.success_threshold:
                logger.info(f"Circuit {self.name}: Closing circuit after {self.metrics.current_success_count} successes")
                self.state = CircuitState.CLOSED
                self.metrics.circuit_closes += 1
                self.metrics.current_success_count = 0
                self.metrics.current_failure_count = 0
                self.last_state_change = time.time()
        
        logger.debug(f"Circuit {self.name}: Success - State: {self.state.value}")
    
    async def _on_failure(self, error: Exception):
        """Handle failed operation"""
        self.metrics.total_requests += 1
        self.metrics.failed_requests += 1
        self.metrics.last_failure_time = time.time()
        
        # Check if this is the expected exception type
        if isinstance(error, self.config.expected_exception):
            self.metrics.current_failure_count += 1
            
            if self.state == CircuitState.CLOSED:
                if self.metrics.current_failure_count >= self.config.failure_threshold:
                    logger.warning(f"Circuit {self.name}: Opening circuit after {self.metrics.current_failure_count} failures")
                    self.state = CircuitState.OPEN
                    self.metrics.circuit_opens += 1
                    self.last_state_change = time.time()
            
            elif self.state == CircuitState.HALF_OPEN:
                logger.warning(f"Circuit {self.name}: Reopening circuit after failure in half-open state")
                self.state = CircuitState.OPEN
                self.metrics.circuit_opens += 1
                self.metrics.current_success_count = 0
                self.last_state_change = time.time()
        
        logger.debug(f"Circuit {self.name}: Failure - State: {self.state.value}, Error: {str(error)}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics"""
        success_rate = 0.0
        if self.metrics.total_requests > 0:
            success_rate = self.metrics.successful_requests / self.metrics.total_requests
        
        return {
            'name': self.name,
            'state': self.state.value,
            'total_requests': self.metrics.total_requests,
            'successful_requests': self.metrics.successful_requests,
            'failed_requests': self.metrics.failed_requests,
            'success_rate': success_rate,
            'circuit_opens': self.metrics.circuit_opens,
            'circuit_closes': self.metrics.circuit_closes,
            'current_failure_count': self.metrics.current_failure_count,
            'current_success_count': self.metrics.current_success_count,
            'last_failure_time': self.metrics.last_failure_time,
            'last_success_time': self.metrics.last_success_time,
            'last_state_change': self.last_state_change,
            'config': {
                'failure_threshold': self.config.failure_threshold,
                'recovery_timeout': self.config.recovery_timeout,
                'success_threshold': self.config.success_threshold,
                'timeout': self.config.timeout
            }
        }
    
    def force_open(self):
        """Force circuit to open"""
        self.state = CircuitState.OPEN
        self.last_state_change = time.time()
        logger.warning(f"Circuit {self.name}: Forced to OPEN state")
    
    def force_close(self):
        """Force circuit to close"""
        self.state = CircuitState.CLOSED
        self.metrics.current_failure_count = 0
        self.metrics.current_success_count = 0
        self.last_state_change = time.time()
        logger.info(f"Circuit {self.name}: Forced to CLOSED state")

class CircuitBreakerManager:
    """Manages multiple circuit breakers"""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.initialize_circuit_breakers()
    
    def initialize_circuit_breakers(self):
        """Initialize circuit breakers for different services"""
        
        # Scraper circuit breakers
        scraper_config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=300.0,  # 5 minutes
            timeout=60.0
        )
        
        for site in ['linkedin', 'indeed', 'remoteok', 'wellfound']:
            self.circuit_breakers[f"scraper_{site}"] = CircuitBreaker(f"scraper_{site}", scraper_config)
        
        # GPT API circuit breaker
        gpt_config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=600.0,  # 10 minutes
            timeout=30.0
        )
        self.circuit_breakers["gpt_api"] = CircuitBreaker("gpt_api", gpt_config)
        
        # Database circuit breaker
        db_config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=120.0,  # 2 minutes
            timeout=10.0
        )
        self.circuit_breakers["database"] = CircuitBreaker("database", db_config)
        
        # Google Sheets circuit breaker
        sheets_config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=300.0,  # 5 minutes
            timeout=30.0
        )
        self.circuit_breakers["google_sheets"] = CircuitBreaker("google_sheets", sheets_config)
    
    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name"""
        return self.circuit_breakers.get(name)
    
    async def call_with_circuit_breaker(self, circuit_name: str, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        circuit = self.get_circuit_breaker(circuit_name)
        if not circuit:
            logger.warning(f"Circuit breaker {circuit_name} not found, executing without protection")
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, func, *args, **kwargs)
        
        return await circuit.call(func, *args, **kwargs)
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get metrics for all circuit breakers"""
        return {
            name: circuit.get_metrics()
            for name, circuit in self.circuit_breakers.items()
        }
    
    def get_health_status(self) -> Dict[str, str]:
        """Get health status for all circuit breakers"""
        return {
            name: circuit.state.value
            for name, circuit in self.circuit_breakers.items()
        }
    
    def force_open_circuit(self, name: str):
        """Force a circuit breaker to open"""
        circuit = self.get_circuit_breaker(name)
        if circuit:
            circuit.force_open()
        else:
            logger.warning(f"Circuit breaker {name} not found")
    
    def force_close_circuit(self, name: str):
        """Force a circuit breaker to close"""
        circuit = self.get_circuit_breaker(name)
        if circuit:
            circuit.force_close()
        else:
            logger.warning(f"Circuit breaker {name} not found")

# Global circuit breaker manager instance
_circuit_breaker_manager: Optional[CircuitBreakerManager] = None

def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """Get global circuit breaker manager instance"""
    global _circuit_breaker_manager
    if _circuit_breaker_manager is None:
        _circuit_breaker_manager = CircuitBreakerManager()
    return _circuit_breaker_manager

def reset_circuit_breaker_manager():
    """Reset global circuit breaker manager (useful for testing)"""
    global _circuit_breaker_manager
    _circuit_breaker_manager = None 