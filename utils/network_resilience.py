import logging
import time
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
from playwright.async_api import Browser, Page, BrowserContext, TimeoutError as PlaywrightTimeoutError
import os

logger = logging.getLogger(__name__)

class ConnectionStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"

@dataclass
class SiteConfig:
    """Configuration for a specific site"""
    name: str
    base_url: str
    timeout: float = 30.0
    max_retries: int = 3
    progressive_timeout: bool = True
    health_check_url: Optional[str] = None
    expected_elements: List[str] = field(default_factory=list)

@dataclass
class ConnectionMetrics:
    """Connection performance metrics"""
    response_time: float
    success_rate: float
    error_count: int
    timeout_count: int
    last_success: Optional[float] = None
    last_failure: Optional[float] = None
    total_requests: int = 0

class NetworkResilienceManager:
    """Manages network resilience including connection pooling, health checks, and timeout handling"""
    
    def __init__(self):
        self.site_configs: Dict[str, SiteConfig] = {}
        self.connection_metrics: Dict[str, ConnectionMetrics] = {}
        self.browser_contexts: List[BrowserContext] = []
        self.max_contexts: int = 5
        self.context_timeout: float = 300.0  # 5 minutes
        self.health_check_interval: float = 60.0  # 1 minute
        self.load_site_configs()
        self.initialize_metrics()
    
    def load_site_configs(self):
        """Load site-specific configurations"""
        self.site_configs = {
            "linkedin": SiteConfig(
                name="LinkedIn",
                base_url="https://www.linkedin.com",
                timeout=45.0,
                max_retries=3,
                progressive_timeout=True,
                health_check_url="https://www.linkedin.com/jobs",
                expected_elements=["article.job-search-card", "div[data-job-id]"]
            ),
            "indeed": SiteConfig(
                name="Indeed",
                base_url="https://www.indeed.com",
                timeout=40.0,
                max_retries=3,
                progressive_timeout=True,
                health_check_url="https://www.indeed.com/jobs",
                expected_elements=["div.job_seen_beacon", "div[data-jk]"]
            ),
            "remoteok": SiteConfig(
                name="RemoteOK",
                base_url="https://remoteok.com",
                timeout=30.0,
                max_retries=2,
                progressive_timeout=False,
                health_check_url="https://remoteok.com/remote-jobs",
                expected_elements=["tr.job", "tr[data-id]"]
            ),
            "wellfound": SiteConfig(
                name="Wellfound",
                base_url="https://wellfound.com",
                timeout=35.0,
                max_retries=3,
                progressive_timeout=True,
                health_check_url="https://wellfound.com/jobs",
                expected_elements=["div[data-testid='job-card']", ".job-card"]
            )
        }
    
    def initialize_metrics(self):
        """Initialize connection metrics for all sites"""
        for site_name in self.site_configs.keys():
            self.connection_metrics[site_name] = ConnectionMetrics(
                response_time=0.0,
                success_rate=1.0,
                error_count=0,
                timeout_count=0
            )
    
    async def get_browser_context(self, browser: Browser, site: str) -> BrowserContext:
        """Get a browser context with connection pooling"""
        # Clean up expired contexts
        await self.cleanup_expired_contexts()
        
        # Try to reuse an existing context
        for context in self.browser_contexts:
            if not context.pages:
                logger.info(f"Reusing existing browser context for {site}")
                return context
        
        # Create new context if under limit
        if len(self.browser_contexts) < self.max_contexts:
            context = await browser.new_context()
            self.browser_contexts.append(context)
            logger.info(f"Created new browser context for {site}")
            return context
        
        # Wait for a context to become available
        logger.warning("All browser contexts in use, waiting for availability...")
        while True:
            await asyncio.sleep(1)
            for context in self.browser_contexts:
                if not context.pages:
                    return context
    
    async def cleanup_expired_contexts(self):
        """Clean up expired browser contexts"""
        current_time = time.time()
        expired_contexts = []
        
        for context in self.browser_contexts:
            try:
                # Check if context is still valid
                pages = context.pages
                if not pages:  # Context is available for reuse
                    continue
                
                # Check if context has been idle too long
                # Note: This is a simplified check - in practice you'd track context creation time
                expired_contexts.append(context)
            except Exception as e:
                logger.warning(f"Context cleanup error: {e}")
                expired_contexts.append(context)
        
        for context in expired_contexts:
            try:
                await context.close()
                self.browser_contexts.remove(context)
                logger.info("Closed expired browser context")
            except Exception as e:
                logger.error(f"Error closing context: {e}")
    
    async def navigate_with_resilience(self, page: Page, url: str, site: str, 
                                     max_retries: Optional[int] = None) -> bool:
        """Navigate to URL with resilience features"""
        config = self.site_configs.get(site, SiteConfig(site, url))
        max_retries = max_retries or config.max_retries
        
        for attempt in range(max_retries + 1):
            try:
                start_time = time.time()
                
                # Calculate timeout for this attempt
                timeout = self.calculate_timeout(config, attempt)
                
                logger.info(f"Navigating to {url} (attempt {attempt + 1}/{max_retries + 1}, timeout: {timeout}s)")
                
                # Navigate with timeout
                await page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")
                
                # Wait for expected elements
                if config.expected_elements:
                    await self.wait_for_expected_elements(page, config.expected_elements, timeout)
                
                # Update metrics
                response_time = time.time() - start_time
                self.update_metrics(site, True, response_time)
                
                logger.info(f"Successfully navigated to {url} in {response_time:.2f}s")
                return True
                
            except PlaywrightTimeoutError as e:
                logger.warning(f"Timeout navigating to {url} (attempt {attempt + 1}): {e}")
                self.update_metrics(site, False, 0.0, timeout_error=True)
                
                if attempt < max_retries:
                    await self.handle_timeout_recovery(page, attempt)
                
            except Exception as e:
                logger.error(f"Error navigating to {url} (attempt {attempt + 1}): {e}")
                self.update_metrics(site, False, 0.0)
                
                if attempt < max_retries:
                    await self.handle_error_recovery(page, attempt)
        
        logger.error(f"Failed to navigate to {url} after {max_retries + 1} attempts")
        return False
    
    def calculate_timeout(self, config: SiteConfig, attempt: int) -> float:
        """Calculate timeout for current attempt"""
        if config.progressive_timeout:
            # Progressive timeout: 30s, 45s, 60s
            return config.timeout + (attempt * 15.0)
        else:
            return config.timeout
    
    async def wait_for_expected_elements(self, page: Page, selectors: List[str], timeout: float):
        """Wait for expected elements to be present"""
        for selector in selectors:
            try:
                await page.wait_for_selector(selector, timeout=timeout * 1000)
                logger.debug(f"Found expected element: {selector}")
                break  # Found at least one expected element
            except PlaywrightTimeoutError:
                logger.warning(f"Expected element not found: {selector}")
                continue
    
    async def handle_timeout_recovery(self, page: Page, attempt: int):
        """Handle timeout recovery strategies"""
        recovery_delay = (attempt + 1) * 2.0  # Progressive delay: 2s, 4s, 6s
        logger.info(f"Applying timeout recovery (delay: {recovery_delay}s)")
        
        # Try to refresh the page
        try:
            await page.reload(timeout=10000)
            await asyncio.sleep(recovery_delay)
        except Exception as e:
            logger.warning(f"Page refresh failed: {e}")
            await asyncio.sleep(recovery_delay)
    
    async def handle_error_recovery(self, page: Page, attempt: int):
        """Handle error recovery strategies"""
        recovery_delay = (attempt + 1) * 1.5  # Progressive delay: 1.5s, 3s, 4.5s
        logger.info(f"Applying error recovery (delay: {recovery_delay}s)")
        
        # Close and recreate page if needed
        try:
            await page.close()
            await asyncio.sleep(recovery_delay)
        except Exception as e:
            logger.warning(f"Page close failed: {e}")
            await asyncio.sleep(recovery_delay)
    
    def update_metrics(self, site: str, success: bool, response_time: float, timeout_error: bool = False):
        """Update connection metrics"""
        if site not in self.connection_metrics:
            self.connection_metrics[site] = ConnectionMetrics(0.0, 1.0, 0, 0)
        
        metrics = self.connection_metrics[site]
        metrics.total_requests += 1
        
        if success:
            metrics.last_success = time.time()
            if metrics.response_time == 0:
                metrics.response_time = response_time
            else:
                metrics.response_time = (metrics.response_time + response_time) / 2
        else:
            metrics.last_failure = time.time()
            metrics.error_count += 1
            if timeout_error:
                metrics.timeout_count += 1
        
        # Update success rate
        success_count = metrics.total_requests - metrics.error_count
        metrics.success_rate = success_count / metrics.total_requests
    
    async def health_check(self, browser: Browser, site: str) -> bool:
        """Perform health check for a site"""
        config = self.site_configs.get(site)
        if not config or not config.health_check_url:
            return True  # No health check configured
        
        try:
            context = await self.get_browser_context(browser, site)
            page = await context.new_page()
            
            logger.info(f"Performing health check for {site}")
            
            success = await self.navigate_with_resilience(
                page, config.health_check_url, site, max_retries=1
            )
            
            await page.close()
            return success
            
        except Exception as e:
            logger.error(f"Health check failed for {site}: {e}")
            return False
    
    async def health_check_all_sites(self, browser: Browser) -> Dict[str, bool]:
        """Perform health check for all sites"""
        results = {}
        
        for site in self.site_configs.keys():
            results[site] = await self.health_check(browser, site)
        
        return results
    
    def get_connection_status(self, site: str) -> ConnectionStatus:
        """Get connection status for a site"""
        if site not in self.connection_metrics:
            return ConnectionStatus.UNKNOWN
        
        metrics = self.connection_metrics[site]
        
        if metrics.success_rate >= 0.9:
            return ConnectionStatus.HEALTHY
        elif metrics.success_rate >= 0.7:
            return ConnectionStatus.DEGRADED
        else:
            return ConnectionStatus.FAILED
    
    def get_site_metrics(self, site: str) -> Dict[str, Any]:
        """Get detailed metrics for a site"""
        if site not in self.connection_metrics:
            return {}
        
        metrics = self.connection_metrics[site]
        config = self.site_configs.get(site)
        
        return {
            "site_name": site,
            "status": self.get_connection_status(site).value,
            "response_time": metrics.response_time,
            "success_rate": metrics.success_rate,
            "total_requests": metrics.total_requests,
            "error_count": metrics.error_count,
            "timeout_count": metrics.timeout_count,
            "last_success": metrics.last_success,
            "last_failure": metrics.last_failure,
            "config": {
                "timeout": config.timeout if config else 30.0,
                "max_retries": config.max_retries if config else 3,
                "progressive_timeout": config.progressive_timeout if config else True
            }
        }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get metrics for all sites"""
        return {
            "sites": {site: self.get_site_metrics(site) for site in self.site_configs.keys()},
            "contexts": {
                "active_contexts": len(self.browser_contexts),
                "max_contexts": self.max_contexts
            }
        }
    
    async def monitor_connections(self, browser: Browser, interval: float = 300.0):
        """Monitor connections continuously"""
        logger.info(f"Starting connection monitoring (interval: {interval}s)")
        
        while True:
            try:
                # Perform health checks
                health_results = await self.health_check_all_sites(browser)
                
                # Log results
                for site, healthy in health_results.items():
                    status = "✅" if healthy else "❌"
                    logger.info(f"{status} {site}: {'Healthy' if healthy else 'Unhealthy'}")
                
                # Log metrics
                metrics = self.get_all_metrics()
                logger.info(f"Connection metrics: {json.dumps(metrics, indent=2)}")
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Connection monitoring error: {e}")
                await asyncio.sleep(interval)

# Global network resilience manager instance
_network_resilience_manager: Optional[NetworkResilienceManager] = None

def get_network_resilience_manager() -> NetworkResilienceManager:
    """Get global network resilience manager instance"""
    global _network_resilience_manager
    if _network_resilience_manager is None:
        _network_resilience_manager = NetworkResilienceManager()
    return _network_resilience_manager

def reset_network_resilience_manager():
    """Reset global network resilience manager (useful for testing)"""
    global _network_resilience_manager
    _network_resilience_manager = None 