import asyncio
import logging
import time
import psutil
import gc
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import json

logger = logging.getLogger(__name__)

class BrowserStatus(Enum):
    """Browser status"""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    RESTARTING = "restarting"

@dataclass
class BrowserMetrics:
    """Browser performance metrics"""
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    active_pages: int = 0
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    last_restart: Optional[float] = None
    uptime_seconds: float = 0.0

@dataclass
class BrowserConfig:
    """Browser configuration"""
    headless: bool = True
    max_pages_per_context: int = 5
    max_contexts: int = 3
    memory_limit_mb: int = 1024  # 1GB
    cpu_limit_percent: int = 80
    restart_interval_minutes: int = 30
    max_operations_before_restart: int = 100
    enable_sandbox: bool = False
    args: List[str] = field(default_factory=lambda: [
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--disable-web-security',
        '--disable-features=VizDisplayCompositor'
    ])

class BrowserManager:
    """Manages Playwright browser instances with resource monitoring and automatic restarts"""
    
    def __init__(self, config: BrowserConfig = None):
        self.config = config or BrowserConfig()
        self.playwright = None
        self.browser = None
        self.contexts: List[BrowserContext] = []
        self.active_pages: List[Page] = []
        
        # Status and metrics
        self.status = BrowserStatus.IDLE
        self.metrics = BrowserMetrics()
        self.start_time = time.time()
        
        # Resource monitoring
        self.monitoring_task = None
        self.monitoring_interval = 30  # seconds
        
        # Operation tracking
        self.operation_count = 0
        self.last_restart_time = 0
        
        # Error tracking
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5
        
        # Callbacks
        self.on_restart_callback: Optional[Callable] = None
        self.on_error_callback: Optional[Callable] = None
    
    async def initialize(self):
        """Initialize browser with resource monitoring"""
        try:
            self.playwright = await async_playwright().start()
            
            self.browser = await self.playwright.chromium.launch(
                headless=self.config.headless,
                args=self.config.args
            )
            
            # Create initial context
            await self._create_context()
            
            # Start resource monitoring
            self.monitoring_task = asyncio.create_task(self._monitor_resources())
            
            self.status = BrowserStatus.IDLE
            self.start_time = time.time()
            self.last_restart_time = time.time()
            
            logger.info("Browser manager initialized successfully")
            
        except Exception as e:
            self.status = BrowserStatus.ERROR
            logger.error(f"Failed to initialize browser manager: {e}")
            raise
    
    async def _create_context(self) -> BrowserContext:
        """Create a new browser context"""
        try:
            context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            
            self.contexts.append(context)
            logger.info(f"Created browser context (total: {len(self.contexts)})")
            return context
            
        except Exception as e:
            logger.error(f"Failed to create browser context: {e}")
            raise
    
    async def get_page(self) -> Optional[Page]:
        """Get an available page or create a new one"""
        try:
            # Check if we need to restart due to resource limits
            if await self._should_restart():
                await self.restart()
            
            # Find available page in existing contexts
            for context in self.contexts:
                pages = context.pages
                if len(pages) < self.config.max_pages_per_context:
                    page = await context.new_page()
                    self.active_pages.append(page)
                    return page
            
            # Create new context if needed
            if len(self.contexts) < self.config.max_contexts:
                context = await self._create_context()
                page = await context.new_page()
                self.active_pages.append(page)
                return page
            
            # Wait for a page to become available
            logger.warning("All browser contexts are at capacity, waiting for available page...")
            return await self._wait_for_available_page()
            
        except Exception as e:
            logger.error(f"Error getting browser page: {e}")
            self.consecutive_errors += 1
            return None
    
    async def _wait_for_available_page(self, timeout: int = 60) -> Optional[Page]:
        """Wait for an available page with timeout"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            for context in self.contexts:
                pages = context.pages
                if len(pages) < self.config.max_pages_per_context:
                    page = await context.new_page()
                    self.active_pages.append(page)
                    return page
            
            await asyncio.sleep(1)
        
        logger.error("Timeout waiting for available browser page")
        return None
    
    async def release_page(self, page: Page):
        """Release a page back to the pool"""
        try:
            if page in self.active_pages:
                self.active_pages.remove(page)
                await page.close()
                logger.debug("Released browser page")
        except Exception as e:
            logger.error(f"Error releasing page: {e}")
    
    async def execute_operation(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute an operation with browser resource management"""
        page = None
        start_time = time.time()
        
        try:
            self.status = BrowserStatus.BUSY
            self.operation_count += 1
            self.metrics.total_operations += 1
            
            # Get page
            page = await self.get_page()
            if not page:
                raise Exception("Failed to get browser page")
            
            # Execute operation
            result = await operation(page, *args, **kwargs)
            
            # Update metrics
            self.metrics.successful_operations += 1
            self.consecutive_errors = 0
            
            logger.debug(f"Browser operation completed successfully in {time.time() - start_time:.2f}s")
            return result
            
        except Exception as e:
            self.metrics.failed_operations += 1
            self.consecutive_errors += 1
            
            logger.error(f"Browser operation failed: {e}")
            
            # Trigger error callback
            if self.on_error_callback:
                await self.on_error_callback(e, self.metrics)
            
            # Check if we need to restart due to errors
            if self.consecutive_errors >= self.max_consecutive_errors:
                logger.critical(f"Too many consecutive errors ({self.consecutive_errors}), restarting browser")
                await self.restart()
            
            raise
            
        finally:
            if page:
                await self.release_page(page)
            
            self.status = BrowserStatus.IDLE
    
    async def _should_restart(self) -> bool:
        """Check if browser should be restarted"""
        current_time = time.time()
        
        # Check restart interval
        if current_time - self.last_restart_time > (self.config.restart_interval_minutes * 60):
            logger.info("Browser restart interval reached")
            return True
        
        # Check operation count
        if self.operation_count >= self.config.max_operations_before_restart:
            logger.info(f"Browser restart due to operation count: {self.operation_count}")
            return True
        
        # Check resource usage
        if await self._check_resource_limits():
            logger.warning("Browser restart due to resource limits")
            return True
        
        return False
    
    async def _check_resource_limits(self) -> bool:
        """Check if resource usage exceeds limits"""
        try:
            # Get process info
            process = psutil.Process()
            memory_info = process.memory_info()
            cpu_percent = process.cpu_percent()
            
            memory_mb = memory_info.rss / 1024 / 1024
            
            self.metrics.memory_usage_mb = memory_mb
            self.metrics.cpu_usage_percent = cpu_percent
            self.metrics.active_pages = len(self.active_pages)
            self.metrics.uptime_seconds = time.time() - self.start_time
            
            # Check limits
            if memory_mb > self.config.memory_limit_mb:
                logger.warning(f"Memory usage exceeded limit: {memory_mb:.1f}MB > {self.config.memory_limit_mb}MB")
                return True
            
            if cpu_percent > self.config.cpu_limit_percent:
                logger.warning(f"CPU usage exceeded limit: {cpu_percent:.1f}% > {self.config.cpu_limit_percent}%")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking resource limits: {e}")
            return False
    
    async def _monitor_resources(self):
        """Monitor browser resources and trigger restarts if needed"""
        while self.status != BrowserStatus.ERROR:
            try:
                await asyncio.sleep(self.monitoring_interval)
                
                # Check resource limits
                if await self._check_resource_limits():
                    logger.warning("Resource limits exceeded during monitoring, restarting browser")
                    await self.restart()
                
                # Log metrics periodically
                if self.operation_count % 10 == 0:
                    logger.info(f"Browser metrics: {self.get_metrics()}")
                
            except Exception as e:
                logger.error(f"Error in resource monitoring: {e}")
    
    async def restart(self):
        """Restart browser with cleanup"""
        try:
            self.status = BrowserStatus.RESTARTING
            logger.info("Restarting browser...")
            
            # Stop monitoring
            if self.monitoring_task:
                self.monitoring_task.cancel()
            
            # Close all pages and contexts
            for page in self.active_pages:
                try:
                    await page.close()
                except:
                    pass
            
            for context in self.contexts:
                try:
                    await context.close()
                except:
                    pass
            
            self.active_pages.clear()
            self.contexts.clear()
            
            # Close browser
            if self.browser:
                await self.browser.close()
            
            # Force garbage collection
            gc.collect()
            
            # Reinitialize
            await self.initialize()
            
            # Reset metrics
            self.operation_count = 0
            self.consecutive_errors = 0
            self.last_restart_time = time.time()
            self.metrics.last_restart = time.time()
            
            # Trigger restart callback
            if self.on_restart_callback:
                await self.on_restart_callback(self.metrics)
            
            logger.info("Browser restarted successfully")
            
        except Exception as e:
            self.status = BrowserStatus.ERROR
            logger.error(f"Failed to restart browser: {e}")
            raise
    
    async def bulk_operations(self, operations: List[Callable], 
                            max_concurrent: int = 3) -> List[Any]:
        """Execute multiple operations with concurrency control"""
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_with_semaphore(operation):
            async with semaphore:
                return await self.execute_operation(operation)
        
        # Execute operations with concurrency limit
        tasks = [execute_with_semaphore(op) for op in operations]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log bulk operation results
        successful = len([r for r in results if not isinstance(r, Exception)])
        failed = len([r for r in results if isinstance(r, Exception)])
        
        logger.info(f"Bulk operations completed: {successful} successful, {failed} failed")
        
        return results
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get browser manager metrics"""
        return {
            'status': self.status.value,
            'operation_count': self.operation_count,
            'consecutive_errors': self.consecutive_errors,
            'active_pages': len(self.active_pages),
            'active_contexts': len(self.contexts),
            'memory_usage_mb': self.metrics.memory_usage_mb,
            'cpu_usage_percent': self.metrics.cpu_usage_percent,
            'uptime_seconds': self.metrics.uptime_seconds,
            'success_rate': (self.metrics.successful_operations / self.metrics.total_operations 
                           if self.metrics.total_operations > 0 else 0),
            'last_restart': self.metrics.last_restart
        }
    
    async def cleanup(self):
        """Clean up browser resources"""
        try:
            self.status = BrowserStatus.ERROR
            
            # Stop monitoring
            if self.monitoring_task:
                self.monitoring_task.cancel()
            
            # Close all pages and contexts
            for page in self.active_pages:
                try:
                    await page.close()
                except:
                    pass
            
            for context in self.contexts:
                try:
                    await context.close()
                except:
                    pass
            
            # Close browser and playwright
            if self.browser:
                await self.browser.close()
            
            if self.playwright:
                await self.playwright.stop()
            
            logger.info("Browser manager cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Error during browser cleanup: {e}")
    
    def set_callbacks(self, on_restart: Callable = None, on_error: Callable = None):
        """Set callback functions"""
        self.on_restart_callback = on_restart
        self.on_error_callback = on_error

# Global instance
_browser_manager = None

def get_browser_manager(config: BrowserConfig = None) -> BrowserManager:
    """Get global browser manager instance"""
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserManager(config)
    return _browser_manager

def reset_browser_manager():
    """Reset global browser manager for testing"""
    global _browser_manager
    if _browser_manager:
        asyncio.create_task(_browser_manager.cleanup())
    _browser_manager = None 