import gspread
import logging
import time
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)

class SheetsErrorType(Enum):
    """Google Sheets API error types"""
    QUOTA_EXCEEDED = "quota_exceeded"
    AUTH_ERROR = "auth_error"
    RATE_LIMIT = "rate_limit"
    NETWORK_ERROR = "network_error"
    PERMISSION_ERROR = "permission_error"
    VALIDATION_ERROR = "validation_error"
    UNKNOWN_ERROR = "unknown_error"

@dataclass
class SheetsOperation:
    """Sheets operation tracking"""
    operation_type: str
    timestamp: float
    data: Dict[str, Any]
    status: str = "pending"
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

@dataclass
class SheetsQuota:
    """Sheets API quota tracking"""
    requests_per_minute: int = 60
    requests_per_day: int = 1000
    current_minute_requests: int = 0
    current_day_requests: int = 0
    last_minute_reset: float = 0
    last_day_reset: float = 0
    quota_exceeded: bool = False
    quota_reset_time: Optional[float] = None

class EnhancedSheetsLogger:
    """Enhanced Google Sheets logger with quota management and error handling"""
    
    def __init__(self, credentials_file: str = None, spreadsheet_id: str = None):
        self.credentials_file = credentials_file
        self.spreadsheet_id = spreadsheet_id
        self.client = None
        self.spreadsheet = None
        self.worksheet = None
        
        # Quota management
        self.quota = SheetsQuota()
        
        # Operation queue for batching
        self.operation_queue = []
        self.max_batch_size = 10
        self.batch_timeout = 30  # seconds
        
        # Error tracking
        self.error_counts = {error_type.value: 0 for error_type in SheetsErrorType}
        self.last_error_time = 0
        self.consecutive_errors = 0
        
        # Retry configuration
        self.base_retry_delay = 1  # seconds
        self.max_retry_delay = 60  # seconds
        self.exponential_backoff = True
        
        # Circuit breaker
        self.circuit_breaker_open = False
        self.circuit_breaker_threshold = 5
        self.circuit_breaker_timeout = 300  # 5 minutes
        self.circuit_breaker_last_failure = 0
        
        # Initialize connection
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize Google Sheets connection with error handling"""
        try:
            if self.credentials_file:
                self.client = gspread.service_account(filename=self.credentials_file)
            else:
                # Try to use default credentials
                self.client = gspread.service_account()
            
            if self.spreadsheet_id:
                self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)
                self.worksheet = self.spreadsheet.sheet1
            
            logger.info("Google Sheets connection initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets connection: {e}")
            self._handle_connection_error(e)
    
    def _handle_connection_error(self, error: Exception):
        """Handle connection errors and update circuit breaker"""
        error_type = self._categorize_error(error)
        self.error_counts[error_type.value] += 1
        self.consecutive_errors += 1
        self.last_error_time = time.time()
        
        if self.consecutive_errors >= self.circuit_breaker_threshold:
            self.circuit_breaker_open = True
            self.circuit_breaker_last_failure = time.time()
            logger.critical(f"Circuit breaker opened for Google Sheets after {self.consecutive_errors} consecutive errors")
        
        # Send alert for critical errors
        if error_type in [SheetsErrorType.AUTH_ERROR, SheetsErrorType.QUOTA_EXCEEDED]:
            self._send_critical_alert(error_type, str(error))
    
    def _categorize_error(self, error: Exception) -> SheetsErrorType:
        """Categorize Google Sheets API errors"""
        error_str = str(error).lower()
        
        if 'quota' in error_str or 'exceeded' in error_str:
            return SheetsErrorType.QUOTA_EXCEEDED
        elif 'auth' in error_str or 'unauthorized' in error_str or 'invalid' in error_str:
            return SheetsErrorType.AUTH_ERROR
        elif 'rate' in error_str or 'limit' in error_str or '429' in error_str:
            return SheetsErrorType.RATE_LIMIT
        elif 'network' in error_str or 'timeout' in error_str or 'connection' in error_str:
            return SheetsErrorType.NETWORK_ERROR
        elif 'permission' in error_str or 'forbidden' in error_str or '403' in error_str:
            return SheetsErrorType.PERMISSION_ERROR
        elif 'validation' in error_str or 'invalid' in error_str:
            return SheetsErrorType.VALIDATION_ERROR
        else:
            return SheetsErrorType.UNKNOWN_ERROR
    
    def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker should be closed"""
        if not self.circuit_breaker_open:
            return True
        
        if time.time() - self.circuit_breaker_last_failure > self.circuit_breaker_timeout:
            self.circuit_breaker_open = False
            self.consecutive_errors = 0
            logger.info("Circuit breaker closed for Google Sheets")
            return True
        
        return False
    
    def _check_quota(self) -> bool:
        """Check if quota allows operation"""
        current_time = time.time()
        
        # Reset minute counter if needed
        if current_time - self.quota.last_minute_reset >= 60:
            self.quota.current_minute_requests = 0
            self.quota.last_minute_reset = current_time
        
        # Reset day counter if needed
        if current_time - self.quota.last_day_reset >= 86400:  # 24 hours
            self.quota.current_day_requests = 0
            self.quota.last_day_reset = current_time
            self.quota.quota_exceeded = False
            self.quota.quota_reset_time = None
        
        # Check if quota is exceeded
        if (self.quota.current_minute_requests >= self.quota.requests_per_minute or
            self.quota.current_day_requests >= self.quota.requests_per_day):
            
            if not self.quota.quota_exceeded:
                self.quota.quota_exceeded = True
                self.quota.quota_reset_time = current_time + 60  # Reset in 1 minute
                logger.critical(f"Google Sheets quota exceeded: {self.quota.current_minute_requests}/min, {self.quota.current_day_requests}/day")
                self._send_critical_alert(SheetsErrorType.QUOTA_EXCEEDED, "Quota exceeded")
            
            return False
        
        return True
    
    def _increment_quota(self):
        """Increment quota counters"""
        self.quota.current_minute_requests += 1
        self.quota.current_day_requests += 1
    
    def _calculate_retry_delay(self, retry_count: int) -> float:
        """Calculate retry delay with exponential backoff"""
        if self.exponential_backoff:
            delay = self.base_retry_delay * (2 ** retry_count)
            return min(delay, self.max_retry_delay)
        else:
            return self.base_retry_delay
    
    async def log_application(self, application_data: Dict[str, Any]) -> bool:
        """Log application to Google Sheets with enhanced error handling"""
        if not self._check_circuit_breaker():
            logger.warning("Circuit breaker is open for Google Sheets")
            return False
        
        if not self._check_quota():
            logger.warning("Google Sheets quota exceeded, queuing operation")
            self._queue_operation("log_application", application_data)
            return False
        
        operation = SheetsOperation(
            operation_type="log_application",
            timestamp=time.time(),
            data=application_data
        )
        
        return await self._execute_operation_with_retry(operation)
    
    async def log_job(self, job_data: Dict[str, Any]) -> bool:
        """Log job to Google Sheets with enhanced error handling"""
        if not self._check_circuit_breaker():
            logger.warning("Circuit breaker is open for Google Sheets")
            return False
        
        if not self._check_quota():
            logger.warning("Google Sheets quota exceeded, queuing operation")
            self._queue_operation("log_job", job_data)
            return False
        
        operation = SheetsOperation(
            operation_type="log_job",
            timestamp=time.time(),
            data=job_data
        )
        
        return await self._execute_operation_with_retry(operation)
    
    async def _execute_operation_with_retry(self, operation: SheetsOperation) -> bool:
        """Execute operation with retry logic"""
        while operation.retry_count < operation.max_retries:
            try:
                # Check quota before each attempt
                if not self._check_quota():
                    await asyncio.sleep(60)  # Wait for quota reset
                    continue
                
                # Execute operation
                if operation.operation_type == "log_application":
                    success = await self._log_application_internal(operation.data)
                elif operation.operation_type == "log_job":
                    success = await self._log_job_internal(operation.data)
                else:
                    logger.error(f"Unknown operation type: {operation.operation_type}")
                    return False
                
                if success:
                    operation.status = "completed"
                    self.consecutive_errors = 0
                    self._increment_quota()
                    logger.info(f"Google Sheets operation completed: {operation.operation_type}")
                    return True
                
                operation.retry_count += 1
                
            except Exception as e:
                operation.retry_count += 1
                operation.error_message = str(e)
                error_type = self._categorize_error(e)
                
                logger.warning(f"Google Sheets operation failed (attempt {operation.retry_count}): {e}")
                
                # Handle specific error types
                if error_type == SheetsErrorType.QUOTA_EXCEEDED:
                    logger.critical("Google Sheets quota exceeded, cannot retry")
                    return False
                elif error_type == SheetsErrorType.AUTH_ERROR:
                    logger.critical("Google Sheets authentication error, cannot retry")
                    return False
                
                # Calculate retry delay
                if operation.retry_count < operation.max_retries:
                    delay = self._calculate_retry_delay(operation.retry_count)
                    logger.info(f"Retrying Google Sheets operation in {delay}s")
                    await asyncio.sleep(delay)
        
        # All retries exhausted
        operation.status = "failed"
        self._handle_connection_error(Exception(f"Operation failed after {operation.max_retries} retries"))
        logger.error(f"Google Sheets operation failed after {operation.max_retries} retries: {operation.error_message}")
        return False
    
    async def _log_application_internal(self, application_data: Dict[str, Any]) -> bool:
        """Internal method to log application data"""
        try:
            if not self.worksheet:
                raise Exception("Worksheet not initialized")
            
            # Prepare row data
            row_data = [
                application_data.get('timestamp', datetime.now().isoformat()),
                application_data.get('job_title', ''),
                application_data.get('company', ''),
                application_data.get('job_url', ''),
                application_data.get('status', 'applied'),
                application_data.get('cover_letter', ''),
                application_data.get('resume_uploaded', False),
                application_data.get('error_message', '')
            ]
            
            # Append row
            self.worksheet.append_row(row_data)
            return True
            
        except Exception as e:
            logger.error(f"Error logging application to Google Sheets: {e}")
            raise
    
    async def _log_job_internal(self, job_data: Dict[str, Any]) -> bool:
        """Internal method to log job data"""
        try:
            if not self.worksheet:
                raise Exception("Worksheet not initialized")
            
            # Prepare row data
            row_data = [
                job_data.get('timestamp', datetime.now().isoformat()),
                job_data.get('title', ''),
                job_data.get('company', ''),
                job_data.get('location', ''),
                job_data.get('source', ''),
                job_data.get('url', ''),
                job_data.get('description', ''),
                job_data.get('salary', ''),
                job_data.get('requirements', '')
            ]
            
            # Append row
            self.worksheet.append_row(row_data)
            return True
            
        except Exception as e:
            logger.error(f"Error logging job to Google Sheets: {e}")
            raise
    
    def _queue_operation(self, operation_type: str, data: Dict[str, Any]):
        """Queue operation for later execution"""
        operation = SheetsOperation(
            operation_type=operation_type,
            timestamp=time.time(),
            data=data
        )
        
        self.operation_queue.append(operation)
        
        # Process queue if it gets too large
        if len(self.operation_queue) >= self.max_batch_size:
            asyncio.create_task(self._process_operation_queue())
    
    async def _process_operation_queue(self):
        """Process queued operations"""
        if not self.operation_queue:
            return
        
        logger.info(f"Processing {len(self.operation_queue)} queued Google Sheets operations")
        
        # Process operations in batches
        while self.operation_queue:
            batch = self.operation_queue[:self.max_batch_size]
            self.operation_queue = self.operation_queue[self.max_batch_size:]
            
            for operation in batch:
                await self._execute_operation_with_retry(operation)
            
            # Wait between batches to respect rate limits
            if self.operation_queue:
                await asyncio.sleep(1)
    
    def _send_critical_alert(self, error_type: SheetsErrorType, message: str):
        """Send critical alert for Google Sheets errors"""
        alert_data = {
            'type': 'google_sheets_error',
            'error_type': error_type.value,
            'message': message,
            'timestamp': time.time(),
            'consecutive_errors': self.consecutive_errors,
            'quota_status': {
                'minute_requests': self.quota.current_minute_requests,
                'day_requests': self.quota.current_day_requests,
                'quota_exceeded': self.quota.quota_exceeded
            }
        }
        
        logger.critical(f"GOOGLE SHEETS CRITICAL ALERT: {json.dumps(alert_data)}")
        
        # TODO: Send alert via monitoring system
        # await self.monitoring_manager.send_alert("google_sheets", alert_data)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get Google Sheets logger metrics"""
        return {
            'connection_status': 'connected' if self.client else 'disconnected',
            'circuit_breaker_open': self.circuit_breaker_open,
            'consecutive_errors': self.consecutive_errors,
            'quota_status': {
                'minute_requests': self.quota.current_minute_requests,
                'day_requests': self.quota.current_day_requests,
                'quota_exceeded': self.quota.quota_exceeded,
                'quota_reset_time': self.quota.quota_reset_time
            },
            'error_counts': self.error_counts,
            'queued_operations': len(self.operation_queue),
            'last_error_time': self.last_error_time
        }
    
    def reset_metrics(self):
        """Reset metrics for testing"""
        self.error_counts = {error_type.value: 0 for error_type in SheetsErrorType}
        self.consecutive_errors = 0
        self.circuit_breaker_open = False
        self.operation_queue = []
        self.quota = SheetsQuota()

# Global instance
_sheets_logger = None

def get_sheets_logger(credentials_file: str = None, spreadsheet_id: str = None) -> EnhancedSheetsLogger:
    """Get global Google Sheets logger instance"""
    global _sheets_logger
    if _sheets_logger is None:
        _sheets_logger = EnhancedSheetsLogger(credentials_file, spreadsheet_id)
    return _sheets_logger

def reset_sheets_logger():
    """Reset global Google Sheets logger for testing"""
    global _sheets_logger
    _sheets_logger = None 