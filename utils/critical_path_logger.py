import logging
import time
import json
import asyncio
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager
from functools import wraps

logger = logging.getLogger(__name__)

class PipelineStage(Enum):
    """Pipeline stages for critical path logging"""
    RESUME_PARSING = "resume_parsing"
    JOB_SCRAPING = "job_scraping"
    GPT_FILTERING = "gpt_filtering"
    AUTO_APPLY = "auto_apply"
    SHEETS_LOGGING = "sheets_logging"
    ERROR_HANDLING = "error_handling"
    CAPTCHA_HANDLING = "captcha_handling"
    BROWSER_MANAGEMENT = "browser_management"

class StageStatus(Enum):
    """Stage execution status"""
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

@dataclass
class StageContext:
    """Context information for pipeline stage"""
    stage: PipelineStage
    start_time: float
    end_time: Optional[float] = None
    status: StageStatus = StageStatus.STARTED
    duration: Optional[float] = None
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PipelineMetrics:
    """Pipeline execution metrics"""
    total_stages: int = 0
    completed_stages: int = 0
    failed_stages: int = 0
    total_duration: float = 0.0
    stage_durations: Dict[str, float] = field(default_factory=dict)
    stage_success_rates: Dict[str, float] = field(default_factory=dict)
    last_execution: Optional[float] = None

class CriticalPathLogger:
    """Comprehensive critical path logging for pipeline stages"""
    
    def __init__(self):
        self.current_context: Optional[StageContext] = None
        self.pipeline_history: List[StageContext] = []
        self.metrics = PipelineMetrics()
        self.alert_callbacks: List[Callable] = []
        
        # Configuration
        self.enable_detailed_logging = True
        self.log_input_output = True
        self.max_log_size = 1000  # Maximum number of stage contexts to keep
        self.stage_timeout = 300  # 5 minutes default timeout
        
        # Performance tracking
        self.slow_stage_threshold = 60  # seconds
        self.critical_stage_threshold = 300  # seconds
    
    def add_alert_callback(self, callback: Callable):
        """Add callback for critical alerts"""
        self.alert_callbacks.append(callback)
    
    @asynccontextmanager
    async def stage_context(self, stage: PipelineStage, 
                          input_data: Optional[Dict[str, Any]] = None,
                          metadata: Optional[Dict[str, Any]] = None):
        """Context manager for pipeline stage logging"""
        context = StageContext(
            stage=stage,
            start_time=time.time(),
            input_data=input_data or {},
            metadata=metadata or {}
        )
        
        self.current_context = context
        self.pipeline_history.append(context)
        
        # Keep only recent history
        if len(self.pipeline_history) > self.max_log_size:
            self.pipeline_history = self.pipeline_history[-self.max_log_size:]
        
        try:
            # Log stage start
            self._log_stage_start(context)
            
            # Set timeout for stage
            stage_task = asyncio.current_task()
            if stage_task:
                stage_task.set_name(f"{stage.value}_{context.start_time}")
            
            yield context
            
            # Log stage completion
            context.status = StageStatus.COMPLETED
            context.end_time = time.time()
            context.duration = context.end_time - context.start_time
            
            self._log_stage_completion(context)
            self._update_metrics(context)
            
        except asyncio.TimeoutError:
            context.status = StageStatus.TIMEOUT
            context.end_time = time.time()
            context.duration = context.end_time - context.start_time
            context.error_message = f"Stage timeout after {self.stage_timeout}s"
            
            self._log_stage_timeout(context)
            self._send_critical_alert(context)
            
        except Exception as e:
            context.status = StageStatus.FAILED
            context.end_time = time.time()
            context.duration = context.end_time - context.start_time
            context.error_message = str(e)
            
            self._log_stage_failure(context)
            self._send_critical_alert(context)
            
            raise
        
        finally:
            self.current_context = None
    
    def _log_stage_start(self, context: StageContext):
        """Log stage start with context"""
        log_data = {
            'stage': context.stage.value,
            'timestamp': context.start_time,
            'input_size': len(str(context.input_data)) if context.input_data else 0,
            'metadata': context.metadata
        }
        
        if self.log_input_output and context.input_data:
            log_data['input_sample'] = self._truncate_data(context.input_data)
        
        logger.info(f"🚀 PIPELINE STAGE STARTED: {context.stage.value} | {json.dumps(log_data)}")
    
    def _log_stage_completion(self, context: StageContext):
        """Log stage completion with metrics"""
        log_data = {
            'stage': context.stage.value,
            'duration': f"{context.duration:.2f}s",
            'status': context.status.value,
            'output_size': len(str(context.output_data)) if context.output_data else 0,
            'metadata': context.metadata
        }
        
        if self.log_input_output and context.output_data:
            log_data['output_sample'] = self._truncate_data(context.output_data)
        
        # Check for slow stages
        if context.duration and context.duration > self.slow_stage_threshold:
            logger.warning(f"⚠️ SLOW STAGE: {context.stage.value} took {context.duration:.2f}s")
        
        if context.duration and context.duration > self.critical_stage_threshold:
            logger.critical(f"🔥 CRITICAL SLOW STAGE: {context.stage.value} took {context.duration:.2f}s")
        
        logger.info(f"✅ PIPELINE STAGE COMPLETED: {context.stage.value} | {json.dumps(log_data)}")
    
    def _log_stage_failure(self, context: StageContext):
        """Log stage failure with error details"""
        log_data = {
            'stage': context.stage.value,
            'duration': f"{context.duration:.2f}s" if context.duration else "N/A",
            'error': context.error_message,
            'retry_count': context.retry_count,
            'metadata': context.metadata
        }
        
        logger.error(f"❌ PIPELINE STAGE FAILED: {context.stage.value} | {json.dumps(log_data)}")
    
    def _log_stage_timeout(self, context: StageContext):
        """Log stage timeout"""
        log_data = {
            'stage': context.stage.value,
            'duration': f"{context.duration:.2f}s" if context.duration else "N/A",
            'timeout_threshold': self.stage_timeout,
            'metadata': context.metadata
        }
        
        logger.critical(f"⏰ PIPELINE STAGE TIMEOUT: {context.stage.value} | {json.dumps(log_data)}")
    
    def _truncate_data(self, data: Any, max_length: int = 200) -> str:
        """Truncate data for logging"""
        data_str = str(data)
        if len(data_str) > max_length:
            return data_str[:max_length] + "..."
        return data_str
    
    def _update_metrics(self, context: StageContext):
        """Update pipeline metrics"""
        self.metrics.total_stages += 1
        
        if context.status == StageStatus.COMPLETED:
            self.metrics.completed_stages += 1
        elif context.status in [StageStatus.FAILED, StageStatus.TIMEOUT]:
            self.metrics.failed_stages += 1
        
        if context.duration:
            stage_name = context.stage.value
            if stage_name not in self.metrics.stage_durations:
                self.metrics.stage_durations[stage_name] = []
            
            self.metrics.stage_durations[stage_name].append(context.duration)
            
            # Keep only recent durations
            if len(self.metrics.stage_durations[stage_name]) > 100:
                self.metrics.stage_durations[stage_name] = self.metrics.stage_durations[stage_name][-100:]
        
        self.metrics.last_execution = time.time()
    
    def _send_critical_alert(self, context: StageContext):
        """Send critical alert for stage failures"""
        alert_data = {
            'type': 'pipeline_stage_failure',
            'stage': context.stage.value,
            'status': context.status.value,
            'duration': context.duration,
            'error_message': context.error_message,
            'timestamp': context.end_time or time.time(),
            'metadata': context.metadata
        }
        
        logger.critical(f"🚨 PIPELINE CRITICAL ALERT: {json.dumps(alert_data)}")
        
        # Send to alert callbacks
        for callback in self.alert_callbacks:
            try:
                asyncio.create_task(callback(alert_data))
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
    
    def log_pipeline_start(self, pipeline_name: str, config: Dict[str, Any]):
        """Log pipeline start"""
        log_data = {
            'pipeline': pipeline_name,
            'timestamp': time.time(),
            'config': config
        }
        
        logger.info(f"🚀 PIPELINE STARTED: {pipeline_name} | {json.dumps(log_data)}")
    
    def log_pipeline_completion(self, pipeline_name: str, results: Dict[str, Any]):
        """Log pipeline completion"""
        log_data = {
            'pipeline': pipeline_name,
            'timestamp': time.time(),
            'results': results,
            'metrics': self.get_pipeline_metrics()
        }
        
        logger.info(f"✅ PIPELINE COMPLETED: {pipeline_name} | {json.dumps(log_data)}")
    
    def log_pipeline_failure(self, pipeline_name: str, error: Exception):
        """Log pipeline failure"""
        log_data = {
            'pipeline': pipeline_name,
            'timestamp': time.time(),
            'error': str(error),
            'metrics': self.get_pipeline_metrics()
        }
        
        logger.critical(f"❌ PIPELINE FAILED: {pipeline_name} | {json.dumps(log_data)}")
    
    def get_pipeline_metrics(self) -> Dict[str, Any]:
        """Get comprehensive pipeline metrics"""
        metrics = {
            'total_stages': self.metrics.total_stages,
            'completed_stages': self.metrics.completed_stages,
            'failed_stages': self.metrics.failed_stages,
            'success_rate': (self.metrics.completed_stages / self.metrics.total_stages 
                           if self.metrics.total_stages > 0 else 0),
            'last_execution': self.metrics.last_execution,
            'stage_metrics': {}
        }
        
        # Calculate stage-specific metrics
        for stage_name, durations in self.metrics.stage_durations.items():
            if durations:
                metrics['stage_metrics'][stage_name] = {
                    'avg_duration': sum(durations) / len(durations),
                    'min_duration': min(durations),
                    'max_duration': max(durations),
                    'total_executions': len(durations)
                }
        
        return metrics
    
    def get_recent_stages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent stage executions"""
        recent = self.pipeline_history[-limit:] if self.pipeline_history else []
        
        return [{
            'stage': ctx.stage.value,
            'status': ctx.status.value,
            'duration': ctx.duration,
            'start_time': ctx.start_time,
            'error_message': ctx.error_message,
            'metadata': ctx.metadata
        } for ctx in recent]
    
    def reset_metrics(self):
        """Reset metrics for testing"""
        self.pipeline_history = []
        self.metrics = PipelineMetrics()
        self.current_context = None

def log_pipeline_stage(stage: PipelineStage, timeout: Optional[int] = None):
    """Decorator for logging pipeline stages"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            logger_instance = get_critical_path_logger()
            
            # Extract input data from args/kwargs
            input_data = {}
            if args:
                input_data['args'] = [str(arg) for arg in args]
            if kwargs:
                input_data['kwargs'] = kwargs
            
            async with logger_instance.stage_context(stage, input_data) as context:
                # Set custom timeout if provided
                if timeout:
                    result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
                else:
                    result = await func(*args, **kwargs)
                
                # Store output data
                context.output_data = {'result': str(result)}
                return result
        
        return wrapper
    return decorator

# Global instance
_critical_path_logger = None

def get_critical_path_logger() -> CriticalPathLogger:
    """Get global critical path logger instance"""
    global _critical_path_logger
    if _critical_path_logger is None:
        _critical_path_logger = CriticalPathLogger()
    return _critical_path_logger

def reset_critical_path_logger():
    """Reset global critical path logger for testing"""
    global _critical_path_logger
    _critical_path_logger = None 