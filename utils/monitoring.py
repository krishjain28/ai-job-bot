import logging
import time
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
from datetime import datetime, timedelta
import statistics
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """Health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

class AlertLevel(Enum):
    """Alert levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class HealthCheck:
    """Health check information"""
    name: str
    status: HealthStatus
    message: str
    timestamp: float
    response_time: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Metric:
    """Metric information"""
    name: str
    value: float
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)

@dataclass
class Alert:
    """Alert information"""
    level: AlertLevel
    message: str
    timestamp: float
    source: str
    details: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False

class MonitoringManager:
    """Comprehensive monitoring and observability system"""
    
    def __init__(self):
        self.health_checks: Dict[str, HealthCheck] = {}
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.alerts: List[Alert] = []
        self.alert_callbacks: Dict[AlertLevel, List[Callable]] = defaultdict(list)
        self.health_check_callbacks: Dict[str, Callable] = {}
        self.initialize_health_checks()
        self.initialize_alert_callbacks()
    
    def initialize_health_checks(self):
        """Initialize health check callbacks"""
        
        # API health checks
        self.health_check_callbacks['openai_api'] = self._check_openai_api_health
        self.health_check_callbacks['mongodb'] = self._check_mongodb_health
        self.health_check_callbacks['google_sheets'] = self._check_google_sheets_health
        self.health_check_callbacks['redis'] = self._check_redis_health
        
        # Scraper health checks
        self.health_check_callbacks['scraper_linkedin'] = self._check_scraper_health
        self.health_check_callbacks['scraper_indeed'] = self._check_scraper_health
        self.health_check_callbacks['scraper_remoteok'] = self._check_scraper_health
        self.health_check_callbacks['scraper_wellfound'] = self._check_scraper_health
    
    def initialize_alert_callbacks(self):
        """Initialize alert callbacks"""
        
        # Critical alerts
        self.alert_callbacks[AlertLevel.CRITICAL] = [
            self._send_critical_alert,
            self._log_critical_alert,
            self._trigger_emergency_response
        ]
        
        # Error alerts
        self.alert_callbacks[AlertLevel.ERROR] = [
            self._send_error_alert,
            self._log_error_alert
        ]
        
        # Warning alerts
        self.alert_callbacks[AlertLevel.WARNING] = [
            self._send_warning_alert,
            self._log_warning_alert
        ]
        
        # Info alerts
        self.alert_callbacks[AlertLevel.INFO] = [
            self._log_info_alert
        ]
    
    async def run_health_checks(self) -> Dict[str, HealthCheck]:
        """Run all health checks"""
        results = {}
        
        for name, callback in self.health_check_callbacks.items():
            try:
                start_time = time.time()
                
                if asyncio.iscoroutinefunction(callback):
                    health_check = await callback(name)
                else:
                    health_check = callback(name)
                
                health_check.response_time = time.time() - start_time
                health_check.timestamp = time.time()
                
                results[name] = health_check
                self.health_checks[name] = health_check
                
                # Trigger alerts for unhealthy services
                if health_check.status == HealthStatus.UNHEALTHY:
                    await self.create_alert(
                        AlertLevel.CRITICAL,
                        f"Service {name} is unhealthy: {health_check.message}",
                        name,
                        health_check.details
                    )
                elif health_check.status == HealthStatus.DEGRADED:
                    await self.create_alert(
                        AlertLevel.WARNING,
                        f"Service {name} is degraded: {health_check.message}",
                        name,
                        health_check.details
                    )
                
            except Exception as e:
                logger.error(f"Health check {name} failed: {e}")
                health_check = HealthCheck(
                    name=name,
                    status=HealthStatus.UNKNOWN,
                    message=f"Health check failed: {str(e)}",
                    timestamp=time.time()
                )
                results[name] = health_check
                self.health_checks[name] = health_check
        
        return results
    
    async def _check_openai_api_health(self, name: str) -> HealthCheck:
        """Check OpenAI API health"""
        try:
            import openai
            client = openai.OpenAI()
            
            start_time = time.time()
            response = client.models.list()
            response_time = time.time() - start_time
            
            if response_time > 5.0:
                return HealthCheck(
                    name=name,
                    status=HealthStatus.DEGRADED,
                    message=f"OpenAI API response time: {response_time:.2f}s",
                    timestamp=time.time(),
                    details={'response_time': response_time, 'models_count': len(response.data)}
                )
            
            return HealthCheck(
                name=name,
                status=HealthStatus.HEALTHY,
                message="OpenAI API is healthy",
                timestamp=time.time(),
                details={'response_time': response_time, 'models_count': len(response.data)}
            )
            
        except Exception as e:
            return HealthCheck(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"OpenAI API health check failed: {str(e)}",
                timestamp=time.time()
            )
    
    async def _check_mongodb_health(self, name: str) -> HealthCheck:
        """Check MongoDB health"""
        try:
            from pymongo import MongoClient
            from config import MONGODB_URI
            
            client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
            start_time = time.time()
            
            # Test connection
            client.admin.command('ping')
            response_time = time.time() - start_time
            
            # Get database stats
            db = client.get_database()
            stats = db.command('dbStats')
            
            client.close()
            
            if response_time > 2.0:
                return HealthCheck(
                    name=name,
                    status=HealthStatus.DEGRADED,
                    message=f"MongoDB response time: {response_time:.2f}s",
                    timestamp=time.time(),
                    details={'response_time': response_time, 'collections': stats.get('collections', 0)}
                )
            
            return HealthCheck(
                name=name,
                status=HealthStatus.HEALTHY,
                message="MongoDB is healthy",
                timestamp=time.time(),
                details={'response_time': response_time, 'collections': stats.get('collections', 0)}
            )
            
        except Exception as e:
            return HealthCheck(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"MongoDB health check failed: {str(e)}",
                timestamp=time.time()
            )
    
    async def _check_google_sheets_health(self, name: str) -> HealthCheck:
        """Check Google Sheets health"""
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            
            # This would require proper Google credentials setup
            # For now, return a placeholder
            return HealthCheck(
                name=name,
                status=HealthStatus.UNKNOWN,
                message="Google Sheets health check not implemented",
                timestamp=time.time()
            )
            
        except Exception as e:
            return HealthCheck(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Google Sheets health check failed: {str(e)}",
                timestamp=time.time()
            )
    
    async def _check_redis_health(self, name: str) -> HealthCheck:
        """Check Redis health"""
        try:
            import redis
            from config import REDIS_URL
            
            if not REDIS_URL:
                return HealthCheck(
                    name=name,
                    status=HealthStatus.UNKNOWN,
                    message="Redis URL not configured",
                    timestamp=time.time()
                )
            
            r = redis.from_url(REDIS_URL, socket_timeout=5)
            start_time = time.time()
            
            r.ping()
            response_time = time.time() - start_time
            
            info = r.info()
            
            return HealthCheck(
                name=name,
                status=HealthStatus.HEALTHY,
                message="Redis is healthy",
                timestamp=time.time(),
                details={
                    'response_time': response_time,
                    'version': info.get('redis_version'),
                    'connected_clients': info.get('connected_clients', 0)
                }
            )
            
        except Exception as e:
            return HealthCheck(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Redis health check failed: {str(e)}",
                timestamp=time.time()
            )
    
    async def _check_scraper_health(self, name: str) -> HealthCheck:
        """Check scraper health"""
        try:
            # This would check scraper-specific metrics
            # For now, return a placeholder
            return HealthCheck(
                name=name,
                status=HealthStatus.HEALTHY,
                message="Scraper health check placeholder",
                timestamp=time.time()
            )
            
        except Exception as e:
            return HealthCheck(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Scraper health check failed: {str(e)}",
                timestamp=time.time()
            )
    
    def record_metric(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a metric"""
        if tags is None:
            tags = {}
        
        metric = Metric(
            name=name,
            value=value,
            timestamp=time.time(),
            tags=tags
        )
        
        self.metrics[name].append(metric)
        
        # Check for metric-based alerts
        self._check_metric_alerts(name, value, tags)
    
    def _check_metric_alerts(self, name: str, value: float, tags: Dict[str, str]):
        """Check if metric should trigger alerts"""
        
        # GPT API cost alerts
        if name == 'gpt_api_cost':
            if value > 100:  # $100 threshold
                asyncio.create_task(self.create_alert(
                    AlertLevel.CRITICAL,
                    f"GPT API cost exceeded threshold: ${value:.2f}",
                    'gpt_api_cost',
                    {'cost': value, 'threshold': 100}
                ))
            elif value > 50:  # $50 threshold
                asyncio.create_task(self.create_alert(
                    AlertLevel.WARNING,
                    f"GPT API cost approaching threshold: ${value:.2f}",
                    'gpt_api_cost',
                    {'cost': value, 'threshold': 100}
                ))
        
        # Response time alerts
        elif name == 'api_response_time':
            if value > 10.0:  # 10 seconds
                asyncio.create_task(self.create_alert(
                    AlertLevel.ERROR,
                    f"API response time too high: {value:.2f}s",
                    'api_response_time',
                    {'response_time': value, 'threshold': 10.0}
                ))
        
        # Error rate alerts
        elif name == 'error_rate':
            if value > 0.1:  # 10% error rate
                asyncio.create_task(self.create_alert(
                    AlertLevel.CRITICAL,
                    f"High error rate detected: {value:.2%}",
                    'error_rate',
                    {'error_rate': value, 'threshold': 0.1}
                ))
    
    async def create_alert(self, level: AlertLevel, message: str, source: str, details: Dict[str, Any] = None):
        """Create and process an alert"""
        if details is None:
            details = {}
        
        alert = Alert(
            level=level,
            message=message,
            timestamp=time.time(),
            source=source,
            details=details
        )
        
        self.alerts.append(alert)
        
        # Keep only last 100 alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
        
        # Execute alert callbacks
        callbacks = self.alert_callbacks.get(level, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"Alert callback {callback.__name__} failed: {e}")
    
    # Alert callback implementations
    
    async def _send_critical_alert(self, alert: Alert):
        """Send critical alert"""
        logger.critical(f"CRITICAL ALERT: {alert.message}")
        # This would integrate with your alerting system (email, Slack, etc.)
    
    async def _send_error_alert(self, alert: Alert):
        """Send error alert"""
        logger.error(f"ERROR ALERT: {alert.message}")
        # This would integrate with your alerting system
    
    async def _send_warning_alert(self, alert: Alert):
        """Send warning alert"""
        logger.warning(f"WARNING ALERT: {alert.message}")
        # This would integrate with your alerting system
    
    def _log_critical_alert(self, alert: Alert):
        """Log critical alert"""
        logger.critical(f"Critical alert from {alert.source}: {alert.message}")
    
    def _log_error_alert(self, alert: Alert):
        """Log error alert"""
        logger.error(f"Error alert from {alert.source}: {alert.message}")
    
    def _log_warning_alert(self, alert: Alert):
        """Log warning alert"""
        logger.warning(f"Warning alert from {alert.source}: {alert.message}")
    
    def _log_info_alert(self, alert: Alert):
        """Log info alert"""
        logger.info(f"Info alert from {alert.source}: {alert.message}")
    
    async def _trigger_emergency_response(self, alert: Alert):
        """Trigger emergency response for critical alerts"""
        logger.critical(f"EMERGENCY RESPONSE TRIGGERED: {alert.message}")
        # This could include:
        # - Pausing all operations
        # - Sending SMS alerts
        # - Creating incident tickets
        # - Scaling down services
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary"""
        total_checks = len(self.health_checks)
        healthy = sum(1 for check in self.health_checks.values() if check.status == HealthStatus.HEALTHY)
        degraded = sum(1 for check in self.health_checks.values() if check.status == HealthStatus.DEGRADED)
        unhealthy = sum(1 for check in self.health_checks.values() if check.status == HealthStatus.UNHEALTHY)
        
        return {
            'total_checks': total_checks,
            'healthy': healthy,
            'degraded': degraded,
            'unhealthy': unhealthy,
            'health_percentage': (healthy / total_checks * 100) if total_checks > 0 else 0,
            'checks': {
                name: {
                    'status': check.status.value,
                    'message': check.message,
                    'response_time': check.response_time,
                    'timestamp': check.timestamp
                }
                for name, check in self.health_checks.items()
            }
        }
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        summary = {}
        
        for metric_name, metric_queue in self.metrics.items():
            if not metric_queue:
                continue
            
            values = [metric.value for metric in metric_queue]
            recent_values = values[-10:]  # Last 10 values
            
            summary[metric_name] = {
                'count': len(values),
                'min': min(values) if values else 0,
                'max': max(values) if values else 0,
                'avg': statistics.mean(values) if values else 0,
                'recent_avg': statistics.mean(recent_values) if recent_values else 0,
                'latest': values[-1] if values else 0,
                'timestamp': metric_queue[-1].timestamp if metric_queue else None
            }
        
        return summary
    
    def get_alerts_summary(self) -> Dict[str, Any]:
        """Get alerts summary"""
        total_alerts = len(self.alerts)
        critical = sum(1 for alert in self.alerts if alert.level == AlertLevel.CRITICAL)
        error = sum(1 for alert in self.alerts if alert.level == AlertLevel.ERROR)
        warning = sum(1 for alert in self.alerts if alert.level == AlertLevel.WARNING)
        info = sum(1 for alert in self.alerts if alert.level == AlertLevel.INFO)
        
        # Recent alerts (last 24 hours)
        cutoff_time = time.time() - 86400
        recent_alerts = [alert for alert in self.alerts if alert.timestamp > cutoff_time]
        
        return {
            'total_alerts': total_alerts,
            'critical': critical,
            'error': error,
            'warning': warning,
            'info': info,
            'recent_alerts_24h': len(recent_alerts),
            'unacknowledged': sum(1 for alert in self.alerts if not alert.acknowledged),
            'recent_alerts': [
                {
                    'level': alert.level.value,
                    'message': alert.message,
                    'source': alert.source,
                    'timestamp': alert.timestamp,
                    'acknowledged': alert.acknowledged
                }
                for alert in self.alerts[-10:]  # Last 10 alerts
            ]
        }
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            'timestamp': time.time(),
            'health': self.get_health_summary(),
            'metrics': self.get_metrics_summary(),
            'alerts': self.get_alerts_summary(),
            'overall_status': self._get_overall_status()
        }
    
    def _get_overall_status(self) -> str:
        """Get overall system status"""
        health_summary = self.get_health_summary()
        alerts_summary = self.get_alerts_summary()
        
        # Check for critical issues
        if health_summary['unhealthy'] > 0 or alerts_summary['critical'] > 0:
            return 'critical'
        
        # Check for warnings
        if health_summary['degraded'] > 0 or alerts_summary['error'] > 0:
            return 'warning'
        
        return 'healthy'

# Global monitoring manager instance
_monitoring_manager: Optional[MonitoringManager] = None

def get_monitoring_manager() -> MonitoringManager:
    """Get global monitoring manager instance"""
    global _monitoring_manager
    if _monitoring_manager is None:
        _monitoring_manager = MonitoringManager()
    return _monitoring_manager

def reset_monitoring_manager():
    """Reset global monitoring manager (useful for testing)"""
    global _monitoring_manager
    _monitoring_manager = None 