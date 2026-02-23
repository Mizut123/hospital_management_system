"""
Security and Audit logging middleware for Hospital Management System.
Implements:
- Audit logging for user actions
- Security headers for all responses
- Rate limiting for API endpoints
- Login attempt tracking
"""
import threading
import time
import logging
from collections import defaultdict
from functools import wraps

from django.conf import settings
from django.http import JsonResponse
from django.core.cache import cache

_thread_locals = threading.local()
security_logger = logging.getLogger('security')


def get_current_user():
    """Get the current user from thread local storage."""
    return getattr(_thread_locals, 'user', None)


def get_current_ip():
    """Get the current IP address from thread local storage."""
    return getattr(_thread_locals, 'ip_address', None)


class AuditLogMiddleware:
    """Middleware to capture user and request info for audit logging."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Store user info in thread local
        _thread_locals.user = request.user if request.user.is_authenticated else None
        _thread_locals.ip_address = self.get_client_ip(request)
        _thread_locals.user_agent = request.META.get('HTTP_USER_AGENT', '')

        response = self.get_response(request)

        # Clean up
        if hasattr(_thread_locals, 'user'):
            del _thread_locals.user
        if hasattr(_thread_locals, 'ip_address'):
            del _thread_locals.ip_address

        return response

    def get_client_ip(self, request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SecurityHeadersMiddleware:
    """
    Middleware to add security headers to all responses.
    Implements OWASP security header recommendations.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Content Security Policy (CSP)
        # Adjust based on your CDN usage (Tailwind, Alpine.js, Chart.js, etc.)
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://cdn.jsdelivr.net https://unpkg.com",
            "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src 'self' data: https:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "form-action 'self'",
            "base-uri 'self'",
        ]
        response['Content-Security-Policy'] = "; ".join(csp_directives)

        # Prevent MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'

        # XSS Protection (legacy but still useful)
        response['X-XSS-Protection'] = '1; mode=block'

        # Prevent clickjacking
        response['X-Frame-Options'] = 'DENY'

        # Referrer Policy - don't leak URLs to external sites
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Permissions Policy - disable unnecessary browser features
        response['Permissions-Policy'] = (
            'accelerometer=(), camera=(), geolocation=(), gyroscope=(), '
            'magnetometer=(), microphone=(), payment=(), usb=()'
        )

        # Cache control for sensitive pages
        if request.path.startswith('/accounts/') or request.path.startswith('/patients/'):
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'

        return response


class RateLimitMiddleware:
    """
    Rate limiting middleware to prevent abuse.
    Uses in-memory storage (for production, use Redis via django-ratelimit).
    """

    # In-memory rate limit tracking (use Redis in production)
    _rate_limits = defaultdict(list)

    def __init__(self, get_response):
        self.get_response = get_response
        # Rate limits: (requests, seconds)
        self.limits = {
            '/accounts/login/': (getattr(settings, 'RATE_LIMIT_LOGIN', 5), 60),
            '/api/': (getattr(settings, 'RATE_LIMIT_API', 60), 60),
            '/search': (getattr(settings, 'RATE_LIMIT_SEARCH', 30), 60),
        }

    def __call__(self, request):
        client_ip = self._get_client_ip(request)

        # Check rate limits for matching paths
        for path_prefix, (max_requests, window) in self.limits.items():
            if request.path.startswith(path_prefix):
                if self._is_rate_limited(client_ip, path_prefix, max_requests, window):
                    security_logger.warning(
                        f"Rate limit exceeded: IP={client_ip}, path={request.path}"
                    )
                    return JsonResponse(
                        {'error': 'Rate limit exceeded. Please try again later.'},
                        status=429
                    )
                self._record_request(client_ip, path_prefix)
                break

        return self.get_response(request)

    def _get_client_ip(self, request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '127.0.0.1')

    def _is_rate_limited(self, client_ip, path_prefix, max_requests, window):
        """Check if the client has exceeded the rate limit."""
        key = f"{client_ip}:{path_prefix}"
        now = time.time()

        # Clean old entries
        self._rate_limits[key] = [
            t for t in self._rate_limits[key] if now - t < window
        ]

        return len(self._rate_limits[key]) >= max_requests

    def _record_request(self, client_ip, path_prefix):
        """Record a request timestamp."""
        key = f"{client_ip}:{path_prefix}"
        self._rate_limits[key].append(time.time())


class LoginAttemptMiddleware:
    """
    Track failed login attempts and lock out accounts after too many failures.
    Implements account lockout protection against brute force attacks.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.max_attempts = getattr(settings, 'MAX_LOGIN_ATTEMPTS', 5)
        self.lockout_duration = getattr(settings, 'LOGIN_LOCKOUT_DURATION', 900)

    def __call__(self, request):
        # Only process POST to login
        if request.path == '/accounts/login/' and request.method == 'POST':
            client_ip = self._get_client_ip(request)
            username = request.POST.get('username', '')

            # Check if locked out
            if self._is_locked_out(client_ip, username):
                security_logger.warning(
                    f"Locked out login attempt: IP={client_ip}, username={username}"
                )
                from django.contrib import messages
                messages.error(
                    request,
                    'Account temporarily locked due to too many failed attempts. '
                    'Please try again later.'
                )

        response = self.get_response(request)

        # Track failed login attempts
        if request.path == '/accounts/login/' and request.method == 'POST':
            if response.status_code == 200 and 'login' in request.path:
                # Still on login page = failed login
                self._record_failed_attempt(
                    self._get_client_ip(request),
                    request.POST.get('username', '')
                )

        return response

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '127.0.0.1')

    def _is_locked_out(self, ip, username):
        """Check if IP or username is locked out."""
        ip_key = f"lockout:ip:{ip}"
        user_key = f"lockout:user:{username}"

        ip_lockout = cache.get(ip_key, 0)
        user_lockout = cache.get(user_key, 0)

        return ip_lockout >= self.max_attempts or user_lockout >= self.max_attempts

    def _record_failed_attempt(self, ip, username):
        """Record a failed login attempt."""
        ip_key = f"lockout:ip:{ip}"
        user_key = f"lockout:user:{username}"

        # Increment attempt counters
        ip_attempts = cache.get(ip_key, 0) + 1
        user_attempts = cache.get(user_key, 0) + 1

        cache.set(ip_key, ip_attempts, self.lockout_duration)
        cache.set(user_key, user_attempts, self.lockout_duration)

        if ip_attempts >= self.max_attempts:
            security_logger.warning(f"IP locked out after {ip_attempts} failed attempts: {ip}")
        if user_attempts >= self.max_attempts:
            security_logger.warning(f"User locked out after {user_attempts} failed attempts: {username}")
