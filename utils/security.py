import logging
import os
import re
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import hashlib
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import pymongo
import openai
import requests

logger = logging.getLogger(__name__)

class ValidationStatus(Enum):
    """Validation status"""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    UNKNOWN = "unknown"

@dataclass
class ValidationResult:
    """Validation result"""
    status: ValidationStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SecurityConfig:
    """Security configuration"""
    encryption_key: Optional[str] = None
    secret_rotation_days: int = 30
    max_failed_attempts: int = 5
    lockout_duration_minutes: int = 15
    require_https: bool = True
    allowed_origins: List[str] = field(default_factory=list)

class SecurityManager:
    """Manages security, secrets, and configuration validation"""
    
    def __init__(self):
        self.config = SecurityConfig()
        self.encryption_key = None
        self.fernet = None
        self.initialize_encryption()
        self.validation_results: Dict[str, ValidationResult] = {}
    
    def initialize_encryption(self):
        """Initialize encryption for secrets"""
        # Get encryption key from environment or generate one
        key = os.getenv('ENCRYPTION_KEY')
        if key:
            self.encryption_key = key.encode()
        else:
            # Generate a new key (in production, this should be stored securely)
            self.encryption_key = Fernet.generate_key()
            logger.warning("No encryption key found, generated new key. Store this securely!")
        
        self.fernet = Fernet(self.encryption_key)
    
    def encrypt_secret(self, secret: str) -> str:
        """Encrypt a secret"""
        if not self.fernet:
            raise Exception("Encryption not initialized")
        
        encrypted = self.fernet.encrypt(secret.encode())
        return base64.b64encode(encrypted).decode()
    
    def decrypt_secret(self, encrypted_secret: str) -> str:
        """Decrypt a secret"""
        if not self.fernet:
            raise Exception("Encryption not initialized")
        
        try:
            encrypted_bytes = base64.b64decode(encrypted_secret.encode())
            decrypted = self.fernet.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt secret: {e}")
            raise
    
    def validate_openai_api_key(self, api_key: str) -> ValidationResult:
        """Validate OpenAI API key format and connectivity"""
        result = ValidationResult(status=ValidationStatus.UNKNOWN, message="")
        
        # Check format
        if not api_key or not api_key.startswith('sk-'):
            result.status = ValidationStatus.INVALID
            result.message = "Invalid OpenAI API key format"
            return result
        
        if len(api_key) < 20:
            result.status = ValidationStatus.INVALID
            result.message = "OpenAI API key too short"
            return result
        
        # Test connectivity
        try:
            client = openai.OpenAI(api_key=api_key)
            # Make a simple test call
            response = client.models.list()
            result.status = ValidationStatus.VALID
            result.message = "OpenAI API key is valid and working"
            result.details = {'models_available': len(response.data)}
        except Exception as e:
            result.status = ValidationStatus.INVALID
            result.message = f"OpenAI API key validation failed: {str(e)}"
        
        return result
    
    def validate_mongodb_uri(self, uri: str) -> ValidationResult:
        """Validate MongoDB URI format and connectivity"""
        result = ValidationResult(status=ValidationStatus.UNKNOWN, message="")
        
        # Check format
        if not uri or not uri.startswith('mongodb'):
            result.status = ValidationStatus.INVALID
            result.message = "Invalid MongoDB URI format"
            return result
        
        # Test connectivity
        try:
            client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
            # Test connection
            client.admin.command('ping')
            result.status = ValidationStatus.VALID
            result.message = "MongoDB URI is valid and connected"
            
            # Get database info
            db_info = client.server_info()
            result.details = {
                'version': db_info.get('version'),
                'host': db_info.get('host'),
                'max_bson_object_size': db_info.get('maxBsonObjectSize')
            }
            
            client.close()
        except Exception as e:
            result.status = ValidationStatus.INVALID
            result.message = f"MongoDB URI validation failed: {str(e)}"
        
        return result
    
    def validate_google_credentials(self, credentials_path: str) -> ValidationResult:
        """Validate Google credentials file"""
        result = ValidationResult(status=ValidationStatus.UNKNOWN, message="")
        
        # Check if file exists
        if not os.path.exists(credentials_path):
            result.status = ValidationStatus.INVALID
            result.message = f"Google credentials file not found: {credentials_path}"
            return result
        
        # Check if it's a valid JSON
        try:
            with open(credentials_path, 'r') as f:
                credentials = json.load(f)
            
            # Check for required fields
            required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
            missing_fields = [field for field in required_fields if field not in credentials]
            
            if missing_fields:
                result.status = ValidationStatus.INVALID
                result.message = f"Missing required fields in Google credentials: {missing_fields}"
                return result
            
            result.status = ValidationStatus.VALID
            result.message = "Google credentials file is valid"
            result.details = {
                'project_id': credentials.get('project_id'),
                'client_email': credentials.get('client_email'),
                'type': credentials.get('type')
            }
            
        except json.JSONDecodeError:
            result.status = ValidationStatus.INVALID
            result.message = "Google credentials file is not valid JSON"
        except Exception as e:
            result.status = ValidationStatus.INVALID
            result.message = f"Google credentials validation failed: {str(e)}"
        
        return result
    
    def validate_email_config(self, smtp_host: str, smtp_port: int, smtp_user: str, smtp_password: str) -> ValidationResult:
        """Validate email configuration"""
        result = ValidationResult(status=ValidationStatus.UNKNOWN, message="")
        
        # Validate SMTP host
        if not smtp_host or not re.match(r'^[a-zA-Z0-9.-]+$', smtp_host):
            result.status = ValidationStatus.INVALID
            result.message = "Invalid SMTP host"
            return result
        
        # Validate SMTP port
        if not isinstance(smtp_port, int) or smtp_port < 1 or smtp_port > 65535:
            result.status = ValidationStatus.INVALID
            result.message = "Invalid SMTP port"
            return result
        
        # Validate email format
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, smtp_user):
            result.status = ValidationStatus.INVALID
            result.message = "Invalid email format"
            return result
        
        # Test SMTP connection (optional, can be slow)
        try:
            import smtplib
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.quit()
            
            result.status = ValidationStatus.VALID
            result.message = "Email configuration is valid and working"
            
        except Exception as e:
            result.status = ValidationStatus.WARNING
            result.message = f"Email configuration validation warning: {str(e)}"
        
        return result
    
    def validate_proxy_config(self, proxy_list: str) -> ValidationResult:
        """Validate proxy configuration"""
        result = ValidationResult(status=ValidationStatus.UNKNOWN, message="")
        
        if not proxy_list:
            result.status = ValidationStatus.WARNING
            result.message = "No proxy configuration provided"
            return result
        
        proxies = proxy_list.split(',')
        valid_proxies = []
        
        for proxy in proxies:
            proxy = proxy.strip()
            if not proxy:
                continue
            
            # Validate proxy format (host:port or host:port:user:pass)
            parts = proxy.split(':')
            if len(parts) not in [2, 4]:
                result.status = ValidationStatus.INVALID
                result.message = f"Invalid proxy format: {proxy}"
                return result
            
            # Validate host
            host = parts[0]
            if not re.match(r'^[a-zA-Z0-9.-]+$', host):
                result.status = ValidationStatus.INVALID
                result.message = f"Invalid proxy host: {host}"
                return result
            
            # Validate port
            try:
                port = int(parts[1])
                if port < 1 or port > 65535:
                    result.status = ValidationStatus.INVALID
                    result.message = f"Invalid proxy port: {port}"
                    return result
            except ValueError:
                result.status = ValidationStatus.INVALID
                result.message = f"Invalid proxy port: {parts[1]}"
                return result
            
            valid_proxies.append(proxy)
        
        result.status = ValidationStatus.VALID
        result.message = f"Proxy configuration is valid ({len(valid_proxies)} proxies)"
        result.details = {'proxy_count': len(valid_proxies)}
        
        return result
    
    def validate_all_configurations(self) -> Dict[str, ValidationResult]:
        """Validate all configuration settings"""
        results = {}
        
        # Validate OpenAI API key
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key:
            results['openai_api_key'] = self.validate_openai_api_key(openai_key)
        else:
            results['openai_api_key'] = ValidationResult(
                ValidationStatus.INVALID, "OpenAI API key not found"
            )
        
        # Validate MongoDB URI
        mongodb_uri = os.getenv('MONGODB_URI')
        if mongodb_uri:
            results['mongodb_uri'] = self.validate_mongodb_uri(mongodb_uri)
        else:
            results['mongodb_uri'] = ValidationResult(
                ValidationStatus.INVALID, "MongoDB URI not found"
            )
        
        # Validate Google credentials
        google_creds = os.getenv('GOOGLE_CREDENTIALS_FILE')
        if google_creds:
            results['google_credentials'] = self.validate_google_credentials(google_creds)
        else:
            results['google_credentials'] = ValidationResult(
                ValidationStatus.WARNING, "Google credentials file not specified"
            )
        
        # Validate email configuration
        smtp_host = os.getenv('SMTP_HOST')
        smtp_port = os.getenv('SMTP_PORT')
        smtp_user = os.getenv('SMTP_USER')
        smtp_password = os.getenv('SMTP_PASSWORD')
        
        if all([smtp_host, smtp_port, smtp_user, smtp_password]):
            try:
                smtp_port_int = int(smtp_port)
                results['email_config'] = self.validate_email_config(
                    smtp_host, smtp_port_int, smtp_user, smtp_password
                )
            except ValueError:
                results['email_config'] = ValidationResult(
                    ValidationStatus.INVALID, "Invalid SMTP port number"
                )
        else:
            results['email_config'] = ValidationResult(
                ValidationStatus.WARNING, "Email configuration incomplete"
            )
        
        # Validate proxy configuration
        proxy_list = os.getenv('PROXY_LIST')
        results['proxy_config'] = self.validate_proxy_config(proxy_list or "")
        
        # Validate Redis configuration
        redis_url = os.getenv('REDIS_URL')
        if redis_url:
            results['redis_config'] = self.validate_redis_config(redis_url)
        else:
            results['redis_config'] = ValidationResult(
                ValidationStatus.WARNING, "Redis URL not specified"
            )
        
        # Validate CAPTCHA configuration
        captcha_key = os.getenv('CAPTCHA_API_KEY')
        if captcha_key:
            results['captcha_config'] = ValidationResult(
                ValidationStatus.VALID, "CAPTCHA API key configured"
            )
        else:
            results['captcha_config'] = ValidationResult(
                ValidationStatus.WARNING, "CAPTCHA API key not specified"
            )
        
        self.validation_results = results
        return results
    
    def validate_redis_config(self, redis_url: str) -> ValidationResult:
        """Validate Redis configuration"""
        result = ValidationResult(status=ValidationStatus.UNKNOWN, message="")
        
        # Check format
        if not redis_url or not redis_url.startswith(('redis://', 'rediss://')):
            result.status = ValidationStatus.INVALID
            result.message = "Invalid Redis URL format"
            return result
        
        # Test connectivity
        try:
            import redis
            r = redis.from_url(redis_url, socket_timeout=5)
            r.ping()
            result.status = ValidationStatus.VALID
            result.message = "Redis configuration is valid and connected"
            
            # Get Redis info
            info = r.info()
            result.details = {
                'version': info.get('redis_version'),
                'used_memory': info.get('used_memory_human'),
                'connected_clients': info.get('connected_clients')
            }
            
        except Exception as e:
            result.status = ValidationStatus.INVALID
            result.message = f"Redis configuration validation failed: {str(e)}"
        
        return result
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of all validation results"""
        if not self.validation_results:
            self.validate_all_configurations()
        
        total = len(self.validation_results)
        valid = sum(1 for r in self.validation_results.values() if r.status == ValidationStatus.VALID)
        invalid = sum(1 for r in self.validation_results.values() if r.status == ValidationStatus.INVALID)
        warnings = sum(1 for r in self.validation_results.values() if r.status == ValidationStatus.WARNING)
        
        critical_errors = []
        for name, result in self.validation_results.items():
            if result.status == ValidationStatus.INVALID:
                critical_errors.append(f"{name}: {result.message}")
        
        return {
            'total_configs': total,
            'valid': valid,
            'invalid': invalid,
            'warnings': warnings,
            'critical_errors': critical_errors,
            'all_valid': invalid == 0,
            'details': self.validation_results
        }
    
    def check_startup_requirements(self) -> bool:
        """Check if all critical startup requirements are met"""
        summary = self.get_validation_summary()
        
        # Critical services that must be valid
        critical_services = ['openai_api_key', 'mongodb_uri']
        
        for service in critical_services:
            if service in self.validation_results:
                result = self.validation_results[service]
                if result.status == ValidationStatus.INVALID:
                    logger.critical(f"Critical service {service} is invalid: {result.message}")
                    return False
        
        if summary['all_valid']:
            logger.info("All startup requirements met")
        else:
            logger.warning(f"Startup requirements check: {summary['valid']}/{summary['total_configs']} valid")
            for error in summary['critical_errors']:
                logger.error(f"Critical error: {error}")
        
        return summary['all_valid']

# Global security manager instance
_security_manager: Optional[SecurityManager] = None

def get_security_manager() -> SecurityManager:
    """Get global security manager instance"""
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager()
    return _security_manager

def reset_security_manager():
    """Reset global security manager (useful for testing)"""
    global _security_manager
    _security_manager = None 