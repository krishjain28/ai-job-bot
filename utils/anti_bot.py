import logging
import time
import random
import json
import requests
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import asyncio
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
import os

logger = logging.getLogger(__name__)

class ProxyStatus(Enum):
    WORKING = "working"
    FAILED = "failed"
    UNTESTED = "untested"
    SLOW = "slow"

@dataclass
class ProxyInfo:
    """Information about a proxy"""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    country: Optional[str] = None
    status: ProxyStatus = ProxyStatus.UNTESTED
    last_tested: Optional[float] = None
    success_rate: float = 0.0
    avg_response_time: float = 0.0
    failure_count: int = 0
    success_count: int = 0
    last_used: Optional[float] = None

@dataclass
class BrowserProfile:
    """Browser fingerprinting profile"""
    user_agent: str
    viewport_width: int
    viewport_height: int
    language: str
    timezone: str
    platform: str
    webgl_vendor: str
    webgl_renderer: str
    canvas_fingerprint: str

class AntiBotManager:
    """Manages anti-bot measures including proxy rotation, CAPTCHA handling, and browser fingerprinting"""
    
    def __init__(self):
        self.proxies: List[ProxyInfo] = []
        self.current_proxy_index = 0
        self.browser_profiles: List[BrowserProfile] = []
        self.current_profile_index = 0
        self.captcha_api_key = os.getenv('CAPTCHA_API_KEY')
        self.proxy_api_key = os.getenv('PROXY_API_KEY')
        self.load_proxies()
        self.load_browser_profiles()
    
    def load_proxies(self):
        """Load proxy list from configuration or API"""
        # Load from environment variables
        proxy_list = os.getenv('PROXY_LIST', '')
        if proxy_list:
            for proxy_str in proxy_list.split(','):
                if ':' in proxy_str:
                    parts = proxy_str.strip().split(':')
                    if len(parts) >= 2:
                        host = parts[0]
                        port = int(parts[1])
                        username = parts[2] if len(parts) > 2 else None
                        password = parts[3] if len(parts) > 3 else None
                        
                        proxy = ProxyInfo(
                            host=host,
                            port=port,
                            username=username,
                            password=password
                        )
                        self.proxies.append(proxy)
        
        # Load from proxy service API (example with Bright Data)
        if self.proxy_api_key:
            self.load_proxies_from_api()
        
        logger.info(f"Loaded {len(self.proxies)} proxies")
    
    def load_proxies_from_api(self):
        """Load proxies from a proxy service API"""
        try:
            # Example with Bright Data
            url = "https://brd.superproxy.io:22225"
            auth = f"{self.proxy_api_key}:"
            
            # Test proxy connection
            proxies = {
                'http': f'http://{auth}@{url}',
                'https': f'http://{auth}@{url}'
            }
            
            response = requests.get('http://httpbin.org/ip', proxies=proxies, timeout=10)
            if response.status_code == 200:
                proxy_info = ProxyInfo(
                    host=url.split(':')[0],
                    port=int(url.split(':')[1]),
                    username=self.proxy_api_key,
                    password=''
                )
                self.proxies.append(proxy_info)
                logger.info("Successfully loaded proxy from API")
        except Exception as e:
            logger.error(f"Failed to load proxy from API: {e}")
    
    def load_browser_profiles(self):
        """Load browser fingerprinting profiles"""
        self.browser_profiles = [
            BrowserProfile(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport_width=1920,
                viewport_height=1080,
                language="en-US",
                timezone="America/New_York",
                platform="MacIntel",
                webgl_vendor="Intel Inc.",
                webgl_renderer="Intel Iris OpenGL Engine",
                canvas_fingerprint="canvas_fp_1"
            ),
            BrowserProfile(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport_width=1366,
                viewport_height=768,
                language="en-US",
                timezone="America/Los_Angeles",
                platform="Win32",
                webgl_vendor="Google Inc. (Intel)",
                webgl_renderer="ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0, D3D11)",
                canvas_fingerprint="canvas_fp_2"
            ),
            BrowserProfile(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport_width=1440,
                viewport_height=900,
                language="en-US",
                timezone="Europe/London",
                platform="Linux x86_64",
                webgl_vendor="Mesa/X.org",
                webgl_renderer="Mesa Intel(R) UHD Graphics 620 (CFL GT2)",
                canvas_fingerprint="canvas_fp_3"
            )
        ]
    
    def get_next_proxy(self) -> Optional[ProxyInfo]:
        """Get the next working proxy"""
        if not self.proxies:
            return None
        
        # Try to find a working proxy
        attempts = 0
        while attempts < len(self.proxies):
            proxy = self.proxies[self.current_proxy_index]
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
            
            if proxy.status == ProxyStatus.WORKING:
                proxy.last_used = time.time()
                return proxy
            
            attempts += 1
        
        # If no working proxies, return the first one
        return self.proxies[0] if self.proxies else None
    
    def get_next_browser_profile(self) -> BrowserProfile:
        """Get the next browser profile for fingerprinting"""
        if not self.browser_profiles:
            # Return a default profile
            return BrowserProfile(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport_width=1920,
                viewport_height=1080,
                language="en-US",
                timezone="America/New_York",
                platform="MacIntel",
                webgl_vendor="Intel Inc.",
                webgl_renderer="Intel Iris OpenGL Engine",
                canvas_fingerprint="canvas_fp_default"
            )
        
        profile = self.browser_profiles[self.current_profile_index]
        self.current_profile_index = (self.current_profile_index + 1) % len(self.browser_profiles)
        return profile
    
    async def create_browser_context(self, browser: Browser, use_proxy: bool = True) -> BrowserContext:
        """Create a browser context with anti-bot measures"""
        profile = self.get_next_browser_profile()
        
        context_options = {
            "viewport": {"width": profile.viewport_width, "height": profile.viewport_height},
            "user_agent": profile.user_agent,
            "locale": profile.language,
            "timezone_id": profile.timezone,
            "extra_http_headers": {
                "Accept-Language": profile.language,
                "Accept-Encoding": "gzip, deflate, br",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
        }
        
        if use_proxy:
            proxy = self.get_next_proxy()
            if proxy:
                proxy_url = f"http://{proxy.host}:{proxy.port}"
                if proxy.username and proxy.password:
                    proxy_url = f"http://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}"
                
                context_options["proxy"] = {
                    "server": proxy_url
                }
        
        context = await browser.new_context(**context_options)
        
        # Add additional fingerprinting
        await self.apply_browser_fingerprinting(context, profile)
        
        return context
    
    async def apply_browser_fingerprinting(self, context: BrowserContext, profile: BrowserProfile):
        """Apply additional browser fingerprinting measures"""
        # Override WebGL vendor and renderer
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Override WebGL
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return '%s';
                }
                if (parameter === 37446) {
                    return '%s';
                }
                return getParameter.call(this, parameter);
            };
        """ % (profile.webgl_vendor, profile.webgl_renderer))
        
        # Override canvas fingerprinting
        await context.add_init_script("""
            const originalGetContext = HTMLCanvasElement.prototype.getContext;
            HTMLCanvasElement.prototype.getContext = function(type, ...args) {
                const context = originalGetContext.call(this, type, ...args);
                if (type === '2d') {
                    const originalFillText = context.fillText;
                    context.fillText = function(text, x, y, ...args) {
                        // Add slight variations to canvas fingerprinting
                        const offset = Math.random() * 0.1;
                        return originalFillText.call(this, text, x + offset, y + offset, ...args);
                    };
                }
                return context;
            };
        """)
    
    async def add_realistic_behavior(self, page: Page):
        """Add realistic mouse movements and delays"""
        # Random mouse movements
        await page.mouse.move(
            random.randint(100, 800),
            random.randint(100, 600)
        )
        
        # Random scroll
        await page.mouse.wheel(0, random.randint(100, 500))
        
        # Random delays
        await page.wait_for_timeout(random.randint(1000, 3000))
    
    async def handle_captcha(self, page: Page) -> bool:
        """Handle CAPTCHA if detected"""
        captcha_selectors = [
            "iframe[src*='recaptcha']",
            "iframe[src*='captcha']",
            ".g-recaptcha",
            "#captcha",
            ".captcha"
        ]
        
        for selector in captcha_selectors:
            try:
                captcha_element = await page.query_selector(selector)
                if captcha_element:
                    logger.warning("CAPTCHA detected, attempting to solve...")
                    return await self.solve_captcha(page, selector)
            except Exception:
                continue
        
        return True  # No CAPTCHA found
    
    async def solve_captcha(self, page: Page, captcha_selector: str) -> bool:
        """Solve CAPTCHA using 2captcha or similar service"""
        if not self.captcha_api_key:
            logger.error("No CAPTCHA API key configured")
            return False
        
        try:
            # Example with 2captcha
            # This is a simplified implementation
            logger.info("Attempting to solve CAPTCHA...")
            
            # Get site key and page URL
            site_key = await page.get_attribute(captcha_selector, "data-sitekey")
            page_url = page.url
            
            if not site_key:
                logger.error("Could not find CAPTCHA site key")
                return False
            
            # Submit to 2captcha
            submit_url = "http://2captcha.com/in.php"
            submit_data = {
                "key": self.captcha_api_key,
                "method": "userrecaptcha",
                "googlekey": site_key,
                "pageurl": page_url,
                "json": 1
            }
            
            response = requests.post(submit_url, data=submit_data)
            result = response.json()
            
            if result.get("status") == 1:
                captcha_id = result.get("request")
                
                # Wait for solution
                for _ in range(30):  # Wait up to 5 minutes
                    await asyncio.sleep(10)
                    
                    check_url = "http://2captcha.com/res.php"
                    check_data = {
                        "key": self.captcha_api_key,
                        "action": "get",
                        "id": captcha_id,
                        "json": 1
                    }
                    
                    check_response = requests.get(check_url, params=check_data)
                    check_result = check_response.json()
                    
                    if check_result.get("status") == 1:
                        solution = check_result.get("request")
                        
                        # Submit solution
                        await page.evaluate(f"""
                            document.getElementById('g-recaptcha-response').innerHTML = '{solution}';
                            ___grecaptcha_cfg.clients[0].aa.l.callback('{solution}');
                        """)
                        
                        logger.info("CAPTCHA solved successfully")
                        return True
                    elif check_result.get("request") != "CAPCHA_NOT_READY":
                        logger.error(f"CAPTCHA solving failed: {check_result}")
                        break
            
            logger.error("Failed to submit CAPTCHA for solving")
            return False
            
        except Exception as e:
            logger.error(f"Error solving CAPTCHA: {e}")
            return False
    
    def test_proxy(self, proxy: ProxyInfo) -> Tuple[bool, float]:
        """Test proxy connectivity and performance"""
        start_time = time.time()
        success = False
        
        try:
            proxy_url = f"http://{proxy.host}:{proxy.port}"
            if proxy.username and proxy.password:
                proxy_url = f"http://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}"
            
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            
            response = requests.get(
                'http://httpbin.org/ip',
                proxies=proxies,
                timeout=10
            )
            
            if response.status_code == 200:
                success = True
                logger.info(f"Proxy {proxy.host}:{proxy.port} working")
            else:
                logger.warning(f"Proxy {proxy.host}:{proxy.port} returned status {response.status_code}")
                
        except Exception as e:
            logger.warning(f"Proxy {proxy.host}:{proxy.port} failed: {e}")
        
        response_time = time.time() - start_time
        
        # Update proxy status
        proxy.last_tested = time.time()
        if success:
            proxy.success_count += 1
            proxy.status = ProxyStatus.WORKING
        else:
            proxy.failure_count += 1
            if proxy.failure_count > 3:
                proxy.status = ProxyStatus.FAILED
        
        # Update success rate
        total_attempts = proxy.success_count + proxy.failure_count
        if total_attempts > 0:
            proxy.success_rate = proxy.success_count / total_attempts
        
        # Update response time
        if proxy.avg_response_time == 0:
            proxy.avg_response_time = response_time
        else:
            proxy.avg_response_time = (proxy.avg_response_time + response_time) / 2
        
        return success, response_time
    
    async def test_all_proxies(self):
        """Test all proxies and update their status"""
        logger.info("Testing all proxies...")
        
        for proxy in self.proxies:
            success, response_time = self.test_proxy(proxy)
            if success:
                logger.info(f"✅ Proxy {proxy.host}:{proxy.port} working (${response_time:.2f}s)")
            else:
                logger.warning(f"❌ Proxy {proxy.host}:{proxy.port} failed")
        
        working_proxies = [p for p in self.proxies if p.status == ProxyStatus.WORKING]
        logger.info(f"Proxy test complete: {len(working_proxies)}/{len(self.proxies)} working")
    
    def get_proxy_stats(self) -> Dict[str, Any]:
        """Get proxy statistics"""
        total_proxies = len(self.proxies)
        working_proxies = len([p for p in self.proxies if p.status == ProxyStatus.WORKING])
        failed_proxies = len([p for p in self.proxies if p.status == ProxyStatus.FAILED])
        
        avg_response_time = 0.0
        if working_proxies > 0:
            response_times = [p.avg_response_time for p in self.proxies if p.status == ProxyStatus.WORKING]
            avg_response_time = sum(response_times) / len(response_times)
        
        return {
            "total_proxies": total_proxies,
            "working_proxies": working_proxies,
            "failed_proxies": failed_proxies,
            "success_rate": working_proxies / total_proxies if total_proxies > 0 else 0.0,
            "avg_response_time": avg_response_time
        }

# Global anti-bot manager instance
_anti_bot_manager: Optional[AntiBotManager] = None

def get_anti_bot_manager() -> AntiBotManager:
    """Get global anti-bot manager instance"""
    global _anti_bot_manager
    if _anti_bot_manager is None:
        _anti_bot_manager = AntiBotManager()
    return _anti_bot_manager

def reset_anti_bot_manager():
    """Reset global anti-bot manager (useful for testing)"""
    global _anti_bot_manager
    _anti_bot_manager = None 