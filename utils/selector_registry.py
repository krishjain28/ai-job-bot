import logging
import time
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SelectorStatus(Enum):
    """Selector health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    BROKEN = "broken"
    UNKNOWN = "unknown"

@dataclass
class SelectorMetrics:
    """Selector performance and health metrics"""
    total_attempts: int = 0
    successful_attempts: int = 0
    fallback_triggers: int = 0
    consecutive_failures: int = 0
    failure_count: int = 0
    last_success: Optional[float] = None
    last_failure: Optional[float] = None
    average_response_time: float = 0.0
    failure_rate: float = 0.0
    status: SelectorStatus = SelectorStatus.UNKNOWN

@dataclass
class SelectorHealth:
    """Selector health information"""
    selector_name: str
    site: str
    status: SelectorStatus
    last_check: float
    failure_count: int = 0
    consecutive_failures: int = 0
    fallback_triggered: bool = False
    error_message: Optional[str] = None

class SelectorRegistry:
    """Enhanced selector registry with health monitoring and automatic validation"""
    
    def __init__(self):
        self.selectors = {}
        self.health_metrics = {}
        self.alert_thresholds = {
            'max_consecutive_failures': 5,
            'max_fallback_triggers_per_run': 10,
            'min_success_rate': 0.8,
            'max_response_time': 5.0  # seconds
        }
        self.health_check_interval = 300  # 5 minutes
        self.last_health_check = 0
        
    def register_selectors(self, site: str, selectors: Dict[str, List[str]]):
        """Register selectors for a site with validation"""
        if site not in self.selectors:
            self.selectors[site] = {}
            self.health_metrics[site] = {}
        
        for selector_name, selector_list in selectors.items():
            self.selectors[site][selector_name] = selector_list
            self.health_metrics[site][selector_name] = SelectorMetrics()
            
        logger.info(f"Registered {len(selectors)} selectors for {site}")
    
    def get_selectors(self, site: str, selector_name: str) -> List[str]:
        """Get selectors for a site and name with health check"""
        if site not in self.selectors or selector_name not in self.selectors[site]:
            logger.error(f"No selectors found for {site}.{selector_name}")
            return []
        
        # Check if health check is needed
        self._check_selector_health(site, selector_name)
        
        return self.selectors[site][selector_name]
    
    def record_selector_attempt(self, site: str, selector_name: str, 
                              selector: str, success: bool, 
                              response_time: float = 0.0, 
                              error_message: Optional[str] = None):
        """Record selector attempt for health monitoring"""
        if site not in self.health_metrics or selector_name not in self.health_metrics[site]:
            return
        
        metrics = self.health_metrics[site][selector_name]
        metrics.total_attempts += 1
        
        if success:
            metrics.successful_attempts += 1
            metrics.last_success = time.time()
            metrics.consecutive_failures = 0
        else:
            metrics.last_failure = time.time()
            metrics.consecutive_failures += 1
            metrics.failure_count += 1
            
            # Log selector failure with context
            logger.warning(f"Selector failed: {site}.{selector_name} -> '{selector}' | "
                          f"Error: {error_message} | "
                          f"Consecutive failures: {metrics.consecutive_failures}")
        
        # Update response time
        if response_time > 0:
            if metrics.average_response_time == 0:
                metrics.average_response_time = response_time
            else:
                metrics.average_response_time = (metrics.average_response_time + response_time) / 2
        
        # Update failure rate
        if metrics.total_attempts > 0:
            metrics.failure_rate = 1 - (metrics.successful_attempts / metrics.total_attempts)
        
        # Update status
        self._update_selector_status(site, selector_name, metrics)
        
        # Check for alerts
        self._check_selector_alerts(site, selector_name, metrics, error_message)
    
    def record_fallback_trigger(self, site: str, selector_name: str):
        """Record when fallback selectors are triggered"""
        if site not in self.health_metrics or selector_name not in self.health_metrics[site]:
            return
        
        metrics = self.health_metrics[site][selector_name]
        metrics.fallback_triggers += 1
        
        logger.warning(f"Fallback triggered for {site}.{selector_name} "
                      f"(total fallbacks: {metrics.fallback_triggers})")
        
        # Alert if too many fallbacks
        if metrics.fallback_triggers >= self.alert_thresholds['max_fallback_triggers_per_run']:
            logger.critical(f"CRITICAL: Excessive fallbacks for {site}.{selector_name} "
                          f"({metrics.fallback_triggers} in this run)")
    
    def _check_selector_health(self, site: str, selector_name: str):
        """Check if selector health validation is needed"""
        current_time = time.time()
        
        # Only check periodically to avoid performance impact
        if current_time - self.last_health_check < self.health_check_interval:
            return
        
        self.last_health_check = current_time
        
        if site not in self.health_metrics or selector_name not in self.health_metrics[site]:
            return
        
        metrics = self.health_metrics[site][selector_name]
        
        # Check for degraded selectors
        if (metrics.failure_rate > (1 - self.alert_thresholds['min_success_rate']) or
            metrics.consecutive_failures >= self.alert_thresholds['max_consecutive_failures'] or
            metrics.average_response_time > self.alert_thresholds['max_response_time']):
            
            logger.warning(f"Selector health check failed for {site}.{selector_name}: "
                          f"failure_rate={metrics.failure_rate:.2f}, "
                          f"consecutive_failures={metrics.consecutive_failures}, "
                          f"avg_response_time={metrics.average_response_time:.2f}s")
    
    def _update_selector_status(self, site: str, selector_name: str, metrics: SelectorMetrics):
        """Update selector status based on metrics"""
        if metrics.failure_rate > 0.5 or metrics.consecutive_failures >= 10:
            metrics.status = SelectorStatus.BROKEN
        elif metrics.failure_rate > 0.2 or metrics.consecutive_failures >= 3:
            metrics.status = SelectorStatus.DEGRADED
        elif metrics.successful_attempts > 0:
            metrics.status = SelectorStatus.HEALTHY
        else:
            metrics.status = SelectorStatus.UNKNOWN
    
    def _check_selector_alerts(self, site: str, selector_name: str, 
                              metrics: SelectorMetrics, error_message: Optional[str] = None):
        """Check for alert conditions and trigger alerts"""
        alert_conditions = []
        
        if metrics.consecutive_failures >= self.alert_thresholds['max_consecutive_failures']:
            alert_conditions.append(f"Consecutive failures: {metrics.consecutive_failures}")
        
        if metrics.failure_rate > (1 - self.alert_thresholds['min_success_rate']):
            alert_conditions.append(f"High failure rate: {metrics.failure_rate:.2f}")
        
        if metrics.average_response_time > self.alert_thresholds['max_response_time']:
            alert_conditions.append(f"Slow response time: {metrics.average_response_time:.2f}s")
        
        if alert_conditions:
            alert_msg = f"SELECTOR ALERT: {site}.{selector_name} | " + " | ".join(alert_conditions)
            if error_message:
                alert_msg += f" | Last error: {error_message}"
            
            logger.critical(alert_msg)
            
            # TODO: Send alert via monitoring system
            # await self.monitoring_manager.send_alert("selector_health", alert_msg)
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report for all selectors"""
        report = {
            'timestamp': time.time(),
            'sites': {},
            'summary': {
                'total_selectors': 0,
                'healthy_selectors': 0,
                'degraded_selectors': 0,
                'broken_selectors': 0,
                'unknown_selectors': 0
            }
        }
        
        for site, selectors in self.health_metrics.items():
            report['sites'][site] = {}
            
            for selector_name, metrics in selectors.items():
                status = metrics.status.value
                report['sites'][site][selector_name] = {
                    'status': status,
                    'total_attempts': metrics.total_attempts,
                    'successful_attempts': metrics.successful_attempts,
                    'failure_rate': metrics.failure_rate,
                    'consecutive_failures': metrics.consecutive_failures,
                    'fallback_triggers': metrics.fallback_triggers,
                    'average_response_time': metrics.average_response_time,
                    'last_success': metrics.last_success,
                    'last_failure': metrics.last_failure
                }
                
                report['summary']['total_selectors'] += 1
                report['summary'][f'{status}_selectors'] += 1
        
        return report
    
    def reset_metrics(self, site: Optional[str] = None, selector_name: Optional[str] = None):
        """Reset metrics for testing or maintenance"""
        if site is None:
            # Reset all metrics
            for site_name in self.health_metrics:
                for selector in self.health_metrics[site_name]:
                    self.health_metrics[site_name][selector] = SelectorMetrics()
        elif selector_name is None:
            # Reset all selectors for a site
            if site in self.health_metrics:
                for selector in self.health_metrics[site]:
                    self.health_metrics[site][selector] = SelectorMetrics()
        else:
            # Reset specific selector
            if site in self.health_metrics and selector_name in self.health_metrics[site]:
                self.health_metrics[site][selector_name] = SelectorMetrics()

# Global instance
_selector_registry = None

def get_selector_registry() -> SelectorRegistry:
    """Get global selector registry instance"""
    global _selector_registry
    if _selector_registry is None:
        _selector_registry = SelectorRegistry()
    return _selector_registry

def reset_selector_registry():
    """Reset global selector registry for testing"""
    global _selector_registry
    _selector_registry = None 