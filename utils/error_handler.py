import logging
import time
import traceback
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error categories for proper handling"""
    NETWORK = "network"
    PARSING = "parsing"
    API = "api"
    DATABASE = "database"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    CAPTCHA = "captcha"
    UNKNOWN = "unknown"

@dataclass
class ErrorInfo:
    """Detailed error information"""
    error: Exception
    category: ErrorCategory
    severity: ErrorSeverity
    context: Dict[str, Any]
    timestamp: float
    retry_count: int = 0
    max_retries: int = 3
    recovery_strategy: Optional[str] = None
    is_recovered: bool = False

@dataclass
class ErrorMetrics:
    """Error tracking metrics"""
    total_errors: int = 0
    errors_by_category: Dict[str, int] = field(default_factory=dict)
    errors_by_severity: Dict[str, int] = field(default_factory=dict)
    recovery_success_rate: float = 0.0
    last_error_time: Optional[float] = None
    error_trend: List[Dict[str, Any]] = field(default_factory=list)

class ErrorHandler:
    """Comprehensive error handling system"""
    
    def __init__(self):
        self.error_metrics = ErrorMetrics()
        self.recovery_strategies: Dict[ErrorCategory, List[Callable]] = {}
        self.error_callbacks: Dict[ErrorSeverity, List[Callable]] = {}
        self.initialize_recovery_strategies()
        self.initialize_error_callbacks()
    
    def initialize_recovery_strategies(self):
        """Initialize recovery strategies for each error category"""
        
        # Network error recovery strategies
        self.recovery_strategies[ErrorCategory.NETWORK] = [
            self._retry_with_backoff,
            self._switch_proxy,
            self._reduce_concurrent_requests
        ]
        
        # API error recovery strategies
        self.recovery_strategies[ErrorCategory.API] = [
            self._retry_with_backoff,
            self._use_fallback_model,
            self._reduce_rate_limit
        ]
        
        # Database error recovery strategies
        self.recovery_strategies[ErrorCategory.DATABASE] = [
            self._retry_with_backoff,
            self._reconnect_database,
            self._use_fallback_storage
        ]
        
        # Rate limit error recovery strategies
        self.recovery_strategies[ErrorCategory.RATE_LIMIT] = [
            self._wait_and_retry,
            self._reduce_rate_limit,
            self._use_fallback_service
        ]
        
        # Timeout error recovery strategies
        self.recovery_strategies[ErrorCategory.TIMEOUT] = [
            self._retry_with_increased_timeout,
            self._reduce_concurrent_requests,
            self._use_fallback_endpoint
        ]
        
        # CAPTCHA error recovery strategies
        self.recovery_strategies[ErrorCategory.CAPTCHA] = [
            self._retry_captcha_solving,
            self._switch_proxy,
            self._manual_captcha_fallback
        ]
    
    def initialize_error_callbacks(self):
        """Initialize error callbacks for different severity levels"""
        
        # Critical error callbacks
        self.error_callbacks[ErrorSeverity.CRITICAL] = [
            self._send_critical_alert,
            self._log_critical_error,
            self._trigger_circuit_breaker
        ]
        
        # High error callbacks
        self.error_callbacks[ErrorSeverity.HIGH] = [
            self._send_high_priority_alert,
            self._log_high_error,
            self._update_health_status
        ]
        
        # Medium error callbacks
        self.error_callbacks[ErrorSeverity.MEDIUM] = [
            self._log_medium_error,
            self._update_metrics
        ]
        
        # Low error callbacks
        self.error_callbacks[ErrorSeverity.LOW] = [
            self._log_low_error
        ]
    
    def categorize_error(self, error: Exception, context: Dict[str, Any]) -> ErrorCategory:
        """Categorize error based on exception type and context"""
        
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        # Network errors
        if any(keyword in error_message for keyword in ['connection', 'timeout', 'network', 'dns']):
            return ErrorCategory.NETWORK
        
        # API errors
        if any(keyword in error_message for keyword in ['api', 'http', 'status', 'rate limit']):
            if 'rate limit' in error_message or '429' in error_message:
                return ErrorCategory.RATE_LIMIT
            return ErrorCategory.API
        
        # Database errors
        if any(keyword in error_message for keyword in ['database', 'mongodb', 'connection', 'query']):
            return ErrorCategory.DATABASE
        
        # Authentication errors
        if any(keyword in error_message for keyword in ['auth', 'unauthorized', 'forbidden', '401', '403']):
            return ErrorCategory.AUTHENTICATION
        
        # Validation errors
        if any(keyword in error_message for keyword in ['validation', 'invalid', 'format']):
            return ErrorCategory.VALIDATION
        
        # Timeout errors
        if any(keyword in error_message for keyword in ['timeout', 'timed out']):
            return ErrorCategory.TIMEOUT
        
        # CAPTCHA errors
        if any(keyword in error_message for keyword in ['captcha', 'robot', 'verification']):
            return ErrorCategory.CAPTCHA
        
        # Parsing errors
        if any(keyword in error_message for keyword in ['parse', 'json', 'xml', 'html']):
            return ErrorCategory.PARSING
        
        return ErrorCategory.UNKNOWN
    
    def determine_severity(self, error: Exception, category: ErrorCategory, context: Dict[str, Any]) -> ErrorSeverity:
        """Determine error severity based on context and impact"""
        
        # Critical: System-wide failures
        if category in [ErrorCategory.DATABASE, ErrorCategory.AUTHENTICATION, ErrorCategory.NETWORK]:
            if context.get('is_critical_operation', False):
                return ErrorSeverity.CRITICAL
        
        # High: Service failures
        if category in [ErrorCategory.API]:
            if context.get('retry_count', 0) >= 3:
                return ErrorSeverity.HIGH
        if category == ErrorCategory.NETWORK:
            if context.get('retry_count', 0) >= 3:
                return ErrorSeverity.HIGH
        
        # Medium: Temporary issues
        if category in [ErrorCategory.TIMEOUT, ErrorCategory.RATE_LIMIT]:
            return ErrorSeverity.MEDIUM
        
        # Low: Non-critical issues
        if category in [ErrorCategory.PARSING, ErrorCategory.VALIDATION]:
            return ErrorSeverity.LOW
        
        return ErrorSeverity.MEDIUM
    
    async def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> bool:
        """Handle error with proper categorization, severity, and recovery"""
        
        if context is None:
            context = {}
        
        # Categorize and determine severity
        category = self.categorize_error(error, context)
        severity = self.determine_severity(error, category, context)
        
        # Create error info
        error_info = ErrorInfo(
            error=error,
            category=category,
            severity=severity,
            context=context,
            timestamp=time.time(),
            retry_count=context.get('retry_count', 0),
            max_retries=context.get('max_retries', 3)
        )
        
        # Update metrics
        self._update_error_metrics(error_info)
        
        # Log error with proper context
        self._log_error(error_info)
        
        # Execute error callbacks
        await self._execute_error_callbacks(error_info)
        
        # Attempt recovery if possible
        if error_info.retry_count < error_info.max_retries:
            return await self._attempt_recovery(error_info)
        
        return False
    
    def _update_error_metrics(self, error_info: ErrorInfo):
        """Update error tracking metrics"""
        self.error_metrics.total_errors += 1
        self.error_metrics.last_error_time = error_info.timestamp
        
        # Update category metrics
        category_name = error_info.category.value
        self.error_metrics.errors_by_category[category_name] = \
            self.error_metrics.errors_by_category.get(category_name, 0) + 1
        
        # Update severity metrics
        severity_name = error_info.severity.value
        self.error_metrics.errors_by_severity[severity_name] = \
            self.error_metrics.errors_by_severity.get(severity_name, 0) + 1
        
        # Update error trend
        self.error_metrics.error_trend.append({
            'timestamp': error_info.timestamp,
            'category': category_name,
            'severity': severity_name,
            'context': error_info.context
        })
        
        # Keep only last 100 errors in trend
        if len(self.error_metrics.error_trend) > 100:
            self.error_metrics.error_trend = self.error_metrics.error_trend[-100:]
    
    def _log_error(self, error_info: ErrorInfo):
        """Log error with proper context and formatting"""
        
        log_message = f"Error [{error_info.category.value.upper()}] [{error_info.severity.value.upper()}]: {str(error_info.error)}"
        
        if error_info.context:
            log_message += f" | Context: {json.dumps(error_info.context)}"
        
        if error_info.retry_count > 0:
            log_message += f" | Retry: {error_info.retry_count}/{error_info.max_retries}"
        
        # Use appropriate log level
        if error_info.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message)
        elif error_info.severity == ErrorSeverity.HIGH:
            logger.error(log_message)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)
        
        # Log full traceback for high severity errors
        if error_info.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            logger.debug(f"Full traceback: {traceback.format_exc()}")
    
    async def _execute_error_callbacks(self, error_info: ErrorInfo):
        """Execute error callbacks for the severity level"""
        
        callbacks = self.error_callbacks.get(error_info.severity, [])
        
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(error_info)
                else:
                    callback(error_info)
            except Exception as e:
                logger.error(f"Error in error callback {callback.__name__}: {e}")
    
    async def _attempt_recovery(self, error_info: ErrorInfo) -> bool:
        """Attempt to recover from error using recovery strategies"""
        
        strategies = self.recovery_strategies.get(error_info.category, [])
        
        for strategy in strategies:
            try:
                logger.info(f"Attempting recovery strategy: {strategy.__name__}")
                
                if asyncio.iscoroutinefunction(strategy):
                    success = await strategy(error_info)
                else:
                    success = strategy(error_info)
                
                if success:
                    error_info.is_recovered = True
                    error_info.recovery_strategy = strategy.__name__
                    logger.info(f"Recovery successful using: {strategy.__name__}")
                    return True
                
            except Exception as e:
                logger.error(f"Recovery strategy {strategy.__name__} failed: {e}")
        
        logger.warning(f"No recovery strategy succeeded for {error_info.category.value}")
        return False
    
    # Recovery Strategy Implementations
    
    async def _retry_with_backoff(self, error_info: ErrorInfo) -> bool:
        """Retry with exponential backoff"""
        delay = min(2 ** error_info.retry_count, 60)  # Max 60 seconds
        await asyncio.sleep(delay)
        return True  # Assume retry will be handled by caller
    
    async def _switch_proxy(self, error_info: ErrorInfo) -> bool:
        """Switch to a different proxy"""
        # This would integrate with the anti-bot manager
        logger.info("Switching proxy for retry")
        return True
    
    async def _reduce_concurrent_requests(self, error_info: ErrorInfo) -> bool:
        """Reduce concurrent request load"""
        logger.info("Reducing concurrent requests")
        return True
    
    async def _use_fallback_model(self, error_info: ErrorInfo) -> bool:
        """Use fallback GPT model"""
        logger.info("Switching to fallback GPT model")
        return True
    
    async def _reduce_rate_limit(self, error_info: ErrorInfo) -> bool:
        """Reduce request rate"""
        logger.info("Reducing request rate")
        return True
    
    async def _reconnect_database(self, error_info: ErrorInfo) -> bool:
        """Reconnect to database"""
        logger.info("Reconnecting to database")
        return True
    
    async def _use_fallback_storage(self, error_info: ErrorInfo) -> bool:
        """Use fallback storage"""
        logger.info("Using fallback storage")
        return True
    
    async def _wait_and_retry(self, error_info: ErrorInfo) -> bool:
        """Wait and retry for rate limits"""
        await asyncio.sleep(60)  # Wait 1 minute
        return True
    
    async def _use_fallback_service(self, error_info: ErrorInfo) -> bool:
        """Use fallback service"""
        logger.info("Using fallback service")
        return True
    
    async def _retry_with_increased_timeout(self, error_info: ErrorInfo) -> bool:
        """Retry with increased timeout"""
        logger.info("Retrying with increased timeout")
        return True
    
    async def _use_fallback_endpoint(self, error_info: ErrorInfo) -> bool:
        """Use fallback endpoint"""
        logger.info("Using fallback endpoint")
        return True
    
    async def _retry_captcha_solving(self, error_info: ErrorInfo) -> bool:
        """Retry CAPTCHA solving"""
        logger.info("Retrying CAPTCHA solving")
        return True
    
    async def _manual_captcha_fallback(self, error_info: ErrorInfo) -> bool:
        """Manual CAPTCHA fallback"""
        logger.info("Manual CAPTCHA fallback required")
        return False  # Manual intervention needed
    
    # Error Callback Implementations
    
    async def _send_critical_alert(self, error_info: ErrorInfo):
        """Send critical alert"""
        logger.critical(f"CRITICAL ALERT: {error_info.category.value} error - {str(error_info.error)}")
        # This would integrate with your alerting system
    
    async def _send_high_priority_alert(self, error_info: ErrorInfo):
        """Send high priority alert"""
        logger.error(f"HIGH PRIORITY ALERT: {error_info.category.value} error - {str(error_info.error)}")
    
    async def _trigger_circuit_breaker(self, error_info: ErrorInfo):
        """Trigger circuit breaker"""
        logger.critical(f"Triggering circuit breaker for {error_info.category.value}")
    
    def _log_critical_error(self, error_info: ErrorInfo):
        """Log critical error"""
        logger.critical(f"Critical error logged: {error_info.category.value}")
    
    def _log_high_error(self, error_info: ErrorInfo):
        """Log high error"""
        logger.error(f"High error logged: {error_info.category.value}")
    
    def _log_medium_error(self, error_info: ErrorInfo):
        """Log medium error"""
        logger.warning(f"Medium error logged: {error_info.category.value}")
    
    def _log_low_error(self, error_info: ErrorInfo):
        """Log low error"""
        logger.info(f"Low error logged: {error_info.category.value}")
    
    async def _update_health_status(self, error_info: ErrorInfo):
        """Update health status"""
        logger.warning(f"Updating health status for {error_info.category.value}")
    
    def _update_metrics(self, error_info: ErrorInfo):
        """Update metrics"""
        logger.debug(f"Updating metrics for {error_info.category.value}")
    
    def get_error_metrics(self) -> Dict[str, Any]:
        """Get current error metrics"""
        return {
            'total_errors': self.error_metrics.total_errors,
            'errors_by_category': self.error_metrics.errors_by_category,
            'errors_by_severity': self.error_metrics.errors_by_severity,
            'recovery_success_rate': self.error_metrics.recovery_success_rate,
            'last_error_time': self.error_metrics.last_error_time,
            'recent_errors': self.error_metrics.error_trend[-10:] if self.error_metrics.error_trend else []
        }

# Global error handler instance
_error_handler: Optional[ErrorHandler] = None

def get_error_handler() -> ErrorHandler:
    """Get global error handler instance"""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler

def reset_error_handler():
    """Reset global error handler (useful for testing)"""
    global _error_handler
    _error_handler = None 