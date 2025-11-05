"""
Security Middleware - Rate Limiting, CSRF Protection, and Request Logging
Enhances application security with multiple layers of protection
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timedelta
from collections import defaultdict
import time
import logging
import hashlib
import secrets
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

# Rate limiting storage (in-memory - use Redis for production)
rate_limit_storage: Dict[str, list] = defaultdict(list)
blocked_ips: Dict[str, datetime] = {}

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware to prevent API abuse
    Configurable limits per endpoint and IP address
    """
    
    def __init__(self, app, requests_per_minute: int = 300, requests_per_hour: int = 5000):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.cleanup_interval = 300  # Cleanup old entries every 5 minutes
        self.last_cleanup = time.time()
    
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Check if IP is blocked
        if client_ip in blocked_ips:
            if datetime.now() < blocked_ips[client_ip]:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Too many requests. Your IP is temporarily blocked."}
                )
            else:
                del blocked_ips[client_ip]
        
        # Get current timestamp
        now = time.time()
        
        # Cleanup old entries periodically
        if now - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_entries()
            self.last_cleanup = now
        
        # Get request history for this IP
        request_times = rate_limit_storage[client_ip]
        
        # Remove requests older than 1 hour
        request_times[:] = [t for t in request_times if now - t < 3600]
        
        # Check hourly limit
        if len(request_times) >= self.requests_per_hour:
            # Block IP for 1 hour
            blocked_ips[client_ip] = datetime.now() + timedelta(hours=1)
            logger.warning(f"IP {client_ip} blocked for exceeding hourly rate limit")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Hourly rate limit exceeded. Try again later."}
            )
        
        # Check per-minute limit
        recent_requests = [t for t in request_times if now - t < 60]
        if len(recent_requests) >= self.requests_per_minute:
            logger.warning(f"IP {client_ip} exceeded per-minute rate limit")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded. Please slow down."}
            )
        
        # Add current request
        request_times.append(now)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(self.requests_per_minute - len(recent_requests) - 1)
        response.headers["X-RateLimit-Reset"] = str(int(now + 60))
        
        return response
    
    def _cleanup_old_entries(self):
        """Remove expired entries from storage"""
        now = time.time()
        expired_ips = []
        
        for ip, times in rate_limit_storage.items():
            # Keep only requests from last hour
            rate_limit_storage[ip] = [t for t in times if now - t < 3600]
            if not rate_limit_storage[ip]:
                expired_ips.append(ip)
        
        # Remove empty entries
        for ip in expired_ips:
            del rate_limit_storage[ip]
        
        logger.info(f"Cleaned up {len(expired_ips)} expired rate limit entries")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs all API requests for security monitoring and debugging
    Includes request details, response status, and timing
    """
    
    async def dispatch(self, request: Request, call_next):
        # Start timing
        start_time = time.time()
        
        # Get request details
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path
        
        # Log request
        logger.info(f"Request: {method} {path} from {client_ip}")
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log response
            logger.info(
                f"Response: {method} {path} - Status: {response.status_code} - "
                f"Duration: {duration:.3f}s - IP: {client_ip}"
            )
            
            # Add response time header
            response.headers["X-Process-Time"] = f"{duration:.3f}"
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Error: {method} {path} - Error: {str(e)} - "
                f"Duration: {duration:.3f}s - IP: {client_ip}"
            )
            raise


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to all responses
    Implements OWASP recommended security headers
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Content Security Policy (adjust as needed)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' ws: wss:;"
        )
        
        return response


# CSRF Token storage (in-memory - use Redis for production)
csrf_tokens: Dict[str, Tuple[str, datetime]] = {}

def generate_csrf_token(user_id: int) -> str:
    """Generate a CSRF token for a user"""
    token = secrets.token_urlsafe(32)
    csrf_tokens[token] = (str(user_id), datetime.now() + timedelta(hours=1))
    return token

def validate_csrf_token(token: str, user_id: int) -> bool:
    """Validate a CSRF token"""
    if token not in csrf_tokens:
        return False
    
    stored_user_id, expiry = csrf_tokens[token]
    
    # Check if token is expired
    if datetime.now() > expiry:
        del csrf_tokens[token]
        return False
    
    # Check if token belongs to user
    if stored_user_id != str(user_id):
        return False
    
    return True

def cleanup_csrf_tokens():
    """Remove expired CSRF tokens"""
    now = datetime.now()
    expired = [token for token, (_, expiry) in csrf_tokens.items() if now > expiry]
    for token in expired:
        del csrf_tokens[token]
    logger.info(f"Cleaned up {len(expired)} expired CSRF tokens")


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """
    Optional IP whitelist for admin endpoints
    Can be configured to restrict access to specific IPs
    """
    
    def __init__(self, app, whitelist: list | None = None, admin_paths: list | None = None):
        super().__init__(app)
        self.whitelist = set(whitelist or [])
        self.admin_paths = admin_paths or ["/api/admin"]
        self.enabled = bool(whitelist)
    
    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)
        
        # Check if this is an admin path
        is_admin_path = any(request.url.path.startswith(path) for path in self.admin_paths)
        
        if is_admin_path:
            client_ip = request.client.host if request.client else "unknown"
            
            if client_ip not in self.whitelist:
                logger.warning(f"Blocked admin access attempt from unauthorized IP: {client_ip}")
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Access denied"}
                )
        
        return await call_next(request)
