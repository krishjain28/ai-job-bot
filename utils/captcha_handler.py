import logging
import time
import asyncio
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum
import json

logger = logging.getLogger(__name__)

class CAPTCHAType(Enum):
    """Types of CAPTCHA challenges"""
    RECAPTCHA = "recaptcha"
    H_CAPTCHA = "hcaptcha"
    IMAGE_CAPTCHA = "image_captcha"
    TEXT_CAPTCHA = "text_captcha"
    UNKNOWN = "unknown"

class CAPTCHAStatus(Enum):
    """CAPTCHA resolution status"""
    PENDING = "pending"
    SOLVED = "solved"
    FAILED = "failed"
    MANUAL_REQUIRED = "manual_required"
    TIMEOUT = "timeout"

@dataclass
class CAPTCHAChallenge:
    """CAPTCHA challenge information"""
    type: CAPTCHAType
    site: str
    url: str
    timestamp: float
    context: Dict[str, Any]
    status: CAPTCHAStatus = CAPTCHAStatus.PENDING
    solution: Optional[str] = None
    error_message: Optional[str] = None
    attempts: int = 0
    max_attempts: int = 3

class CAPTCHAHandler:
    """Comprehensive CAPTCHA handling with manual fallback and alerting"""
    
    def __init__(self):
        self.challenges = []
        self.manual_fallback_enabled = True
        self.auto_solve_timeout = 30  # seconds
        self.manual_timeout = 300  # 5 minutes for manual solving
        self.max_manual_fallbacks_per_run = 5
        self.manual_fallbacks_this_run = 0
        
        # Callbacks for different CAPTCHA types
        self.solvers = {
            CAPTCHAType.RECAPTCHA: self._solve_recaptcha,
            CAPTCHAType.H_CAPTCHA: self._solve_hcaptcha,
            CAPTCHAType.IMAGE_CAPTCHA: self._solve_image_captcha,
            CAPTCHAType.TEXT_CAPTCHA: self._solve_text_captcha,
        }
        
        # Manual fallback callback
        self.manual_fallback_callback: Optional[Callable] = None
    
    def set_manual_fallback_callback(self, callback: Callable):
        """Set callback for manual CAPTCHA solving"""
        self.manual_fallback_callback = callback
    
    async def handle_captcha(self, page, site: str, url: str, 
                           context: Dict[str, Any] = None) -> bool:
        """Handle CAPTCHA detection and solving"""
        if context is None:
            context = {}
        
        # Detect CAPTCHA type
        captcha_type = await self._detect_captcha_type(page)
        
        if captcha_type == CAPTCHAType.UNKNOWN:
            logger.info(f"No CAPTCHA detected on {site}")
            return True
        
        # Create challenge record
        challenge = CAPTCHAChallenge(
            type=captcha_type,
            site=site,
            url=url,
            timestamp=time.time(),
            context=context
        )
        
        self.challenges.append(challenge)
        
        logger.warning(f"CAPTCHA detected on {site}: {captcha_type.value}")
        
        # Try automatic solving first
        if await self._attempt_auto_solve(challenge, page):
            return True
        
        # Fall back to manual solving if enabled
        if self.manual_fallback_enabled:
            return await self._handle_manual_fallback(challenge, page)
        
        logger.error(f"CAPTCHA solving failed for {site}: {captcha_type.value}")
        return False
    
    async def _detect_captcha_type(self, page) -> CAPTCHAType:
        """Detect CAPTCHA type on the page"""
        try:
            # Check for reCAPTCHA
            recaptcha_selectors = [
                'iframe[src*="recaptcha"]',
                '.g-recaptcha',
                '#recaptcha',
                '[data-sitekey]'
            ]
            
            for selector in recaptcha_selectors:
                if await page.query_selector(selector):
                    return CAPTCHAType.RECAPTCHA
            
            # Check for hCaptcha
            hcaptcha_selectors = [
                'iframe[src*="hcaptcha"]',
                '.h-captcha',
                '#hcaptcha'
            ]
            
            for selector in hcaptcha_selectors:
                if await page.query_selector(selector):
                    return CAPTCHAType.H_CAPTCHA
            
            # Check for image CAPTCHA
            image_captcha_selectors = [
                'img[src*="captcha"]',
                '.captcha-image',
                '#captcha-image'
            ]
            
            for selector in image_captcha_selectors:
                if await page.query_selector(selector):
                    return CAPTCHAType.IMAGE_CAPTCHA
            
            # Check for text CAPTCHA
            text_captcha_selectors = [
                'input[name*="captcha"]',
                '.captcha-input',
                '#captcha-input'
            ]
            
            for selector in text_captcha_selectors:
                if await page.query_selector(selector):
                    return CAPTCHAType.TEXT_CAPTCHA
            
            return CAPTCHAType.UNKNOWN
            
        except Exception as e:
            logger.error(f"Error detecting CAPTCHA type: {e}")
            return CAPTCHAType.UNKNOWN
    
    async def _attempt_auto_solve(self, challenge: CAPTCHAChallenge, page) -> bool:
        """Attempt automatic CAPTCHA solving"""
        challenge.attempts += 1
        
        try:
            solver = self.solvers.get(challenge.type)
            if not solver:
                logger.warning(f"No solver available for CAPTCHA type: {challenge.type.value}")
                return False
            
            logger.info(f"Attempting auto-solve for {challenge.type.value} on {challenge.site}")
            
            # Set timeout for auto-solving
            start_time = time.time()
            
            # Try to solve
            solution = await asyncio.wait_for(
                solver(challenge, page),
                timeout=self.auto_solve_timeout
            )
            
            if solution:
                challenge.solution = solution
                challenge.status = CAPTCHAStatus.SOLVED
                logger.info(f"CAPTCHA auto-solved successfully for {challenge.site}")
                return True
            
            challenge.status = CAPTCHAStatus.FAILED
            challenge.error_message = "Auto-solving failed"
            logger.warning(f"CAPTCHA auto-solving failed for {challenge.site}")
            return False
            
        except asyncio.TimeoutError:
            challenge.status = CAPTCHAStatus.TIMEOUT
            challenge.error_message = "Auto-solving timeout"
            logger.warning(f"CAPTCHA auto-solving timeout for {challenge.site}")
            return False
        except Exception as e:
            challenge.status = CAPTCHAStatus.FAILED
            challenge.error_message = str(e)
            logger.error(f"CAPTCHA auto-solving error for {challenge.site}: {e}")
            return False
    
    async def _handle_manual_fallback(self, challenge: CAPTCHAChallenge, page) -> bool:
        """Handle manual CAPTCHA solving fallback"""
        if self.manual_fallbacks_this_run >= self.max_manual_fallbacks_per_run:
            logger.critical(f"Maximum manual fallbacks reached ({self.max_manual_fallbacks_per_run})")
            return False
        
        self.manual_fallbacks_this_run += 1
        challenge.status = CAPTCHAStatus.MANUAL_REQUIRED
        
        logger.critical(f"MANUAL CAPTCHA FALLBACK REQUIRED: {challenge.site} | "
                       f"Type: {challenge.type.value} | "
                       f"URL: {challenge.url} | "
                       f"Manual fallbacks this run: {self.manual_fallbacks_this_run}")
        
        # Send alert
        await self._send_manual_captcha_alert(challenge)
        
        # Call manual fallback callback if set
        if self.manual_fallback_callback:
            try:
                return await self.manual_fallback_callback(challenge, page)
            except Exception as e:
                logger.error(f"Manual fallback callback error: {e}")
        
        # Default manual fallback behavior
        return await self._default_manual_fallback(challenge, page)
    
    async def _default_manual_fallback(self, challenge: CAPTCHAChallenge, page) -> bool:
        """Default manual fallback behavior"""
        logger.info(f"Waiting for manual CAPTCHA solving on {challenge.site}...")
        
        try:
            # Wait for manual solving with timeout
            start_time = time.time()
            
            while time.time() - start_time < self.manual_timeout:
                # Check if CAPTCHA is solved (this is a simplified check)
                captcha_inputs = await page.query_selector_all('input[name*="captcha"]')
                
                for input_elem in captcha_inputs:
                    value = await input_elem.input_value()
                    if value and len(value) > 3:  # Assume solved if input has content
                        challenge.solution = value
                        challenge.status = CAPTCHAStatus.SOLVED
                        logger.info(f"Manual CAPTCHA solving detected for {challenge.site}")
                        return True
                
                await asyncio.sleep(2)  # Check every 2 seconds
            
            challenge.status = CAPTCHAStatus.TIMEOUT
            challenge.error_message = "Manual solving timeout"
            logger.error(f"Manual CAPTCHA solving timeout for {challenge.site}")
            return False
            
        except Exception as e:
            challenge.status = CAPTCHAStatus.FAILED
            challenge.error_message = str(e)
            logger.error(f"Manual CAPTCHA fallback error for {challenge.site}: {e}")
            return False
    
    async def _solve_recaptcha(self, challenge: CAPTCHAChallenge, page) -> Optional[str]:
        """Solve reCAPTCHA (placeholder for integration with solving service)"""
        # TODO: Integrate with 2captcha, anti-captcha, or similar service
        logger.info("reCAPTCHA solving not implemented - would integrate with solving service")
        return None
    
    async def _solve_hcaptcha(self, challenge: CAPTCHAChallenge, page) -> Optional[str]:
        """Solve hCaptcha (placeholder for integration with solving service)"""
        # TODO: Integrate with 2captcha, anti-captcha, or similar service
        logger.info("hCaptcha solving not implemented - would integrate with solving service")
        return None
    
    async def _solve_image_captcha(self, challenge: CAPTCHAChallenge, page) -> Optional[str]:
        """Solve image CAPTCHA (placeholder for OCR integration)"""
        # TODO: Integrate with OCR service or image recognition
        logger.info("Image CAPTCHA solving not implemented - would integrate with OCR service")
        return None
    
    async def _solve_text_captcha(self, challenge: CAPTCHAChallenge, page) -> Optional[str]:
        """Solve text CAPTCHA (placeholder for text recognition)"""
        # TODO: Integrate with text recognition service
        logger.info("Text CAPTCHA solving not implemented - would integrate with text recognition")
        return None
    
    async def _send_manual_captcha_alert(self, challenge: CAPTCHAChallenge):
        """Send alert for manual CAPTCHA solving requirement"""
        alert_data = {
            'type': 'manual_captcha_required',
            'site': challenge.site,
            'captcha_type': challenge.type.value,
            'url': challenge.url,
            'timestamp': challenge.timestamp,
            'manual_fallbacks_this_run': self.manual_fallbacks_this_run,
            'context': challenge.context
        }
        
        logger.critical(f"MANUAL CAPTCHA ALERT: {json.dumps(alert_data)}")
        
        # TODO: Send alert via monitoring system
        # await self.monitoring_manager.send_alert("manual_captcha", alert_data)
    
    def get_captcha_metrics(self) -> Dict[str, Any]:
        """Get CAPTCHA handling metrics"""
        total_challenges = len(self.challenges)
        solved_challenges = len([c for c in self.challenges if c.status == CAPTCHAStatus.SOLVED])
        manual_fallbacks = len([c for c in self.challenges if c.status == CAPTCHAStatus.MANUAL_REQUIRED])
        failed_challenges = len([c for c in self.challenges if c.status == CAPTCHAStatus.FAILED])
        
        return {
            'total_challenges': total_challenges,
            'solved_challenges': solved_challenges,
            'manual_fallbacks': manual_fallbacks,
            'failed_challenges': failed_challenges,
            'success_rate': solved_challenges / total_challenges if total_challenges > 0 else 0,
            'manual_fallback_rate': manual_fallbacks / total_challenges if total_challenges > 0 else 0,
            'manual_fallbacks_this_run': self.manual_fallbacks_this_run,
            'max_manual_fallbacks_per_run': self.max_manual_fallbacks_per_run
        }
    
    def reset_metrics(self):
        """Reset metrics for testing"""
        self.challenges = []
        self.manual_fallbacks_this_run = 0

# Global instance
_captcha_handler = None

def get_captcha_handler() -> CAPTCHAHandler:
    """Get global CAPTCHA handler instance"""
    global _captcha_handler
    if _captcha_handler is None:
        _captcha_handler = CAPTCHAHandler()
    return _captcha_handler

def reset_captcha_handler():
    """Reset global CAPTCHA handler for testing"""
    global _captcha_handler
    _captcha_handler = None 