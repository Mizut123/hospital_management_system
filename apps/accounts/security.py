"""
Security utilities for the Hospital Management System.
Implements:
- Field-level encryption for PHI (Protected Health Information)
- Input validation and sanitization
- CSRF protection decorators for API views
- Access control helpers
"""
import base64
import hashlib
import hmac
import re
import logging
from functools import wraps

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.core.exceptions import PermissionDenied

security_logger = logging.getLogger('security')

# =============================================================================
# FIELD ENCRYPTION
# =============================================================================

try:
    from cryptography.fernet import Fernet, InvalidToken
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False
    security_logger.warning("cryptography package not installed. Field encryption unavailable.")


class FieldEncryption:
    """
    Handles encryption/decryption of sensitive fields.
    Uses Fernet symmetric encryption (AES-128-CBC with HMAC).
    """

    def __init__(self):
        self.key = settings.FIELD_ENCRYPTION_KEY
        self._fernet = None

    @property
    def fernet(self):
        """Lazy initialization of Fernet cipher."""
        if self._fernet is None and self.key and ENCRYPTION_AVAILABLE:
            try:
                self._fernet = Fernet(self.key.encode() if isinstance(self.key, str) else self.key)
            except Exception as e:
                security_logger.error(f"Failed to initialize encryption: {e}")
        return self._fernet

    def encrypt(self, value):
        """Encrypt a string value."""
        if not value:
            return value
        if not self.fernet:
            security_logger.warning("Encryption not available, storing value unencrypted")
            return value
        try:
            return self.fernet.encrypt(value.encode()).decode()
        except Exception as e:
            security_logger.error(f"Encryption failed: {e}")
            return value

    def decrypt(self, value):
        """Decrypt an encrypted value."""
        if not value:
            return value
        if not self.fernet:
            return value
        try:
            return self.fernet.decrypt(value.encode()).decode()
        except InvalidToken:
            # Value might not be encrypted (legacy data)
            return value
        except Exception as e:
            security_logger.error(f"Decryption failed: {e}")
            return value

    def hash_for_lookup(self, value):
        """
        Create a searchable hash of a value.
        Use this for indexed lookups on encrypted fields.
        """
        if not value:
            return None
        # Use HMAC-SHA256 with the encryption key as the secret
        secret = (self.key or 'default-secret').encode()
        return hmac.new(secret, value.encode(), hashlib.sha256).hexdigest()


# Global encryption instance
field_encryption = FieldEncryption()


def encrypt_field(value):
    """Convenience function to encrypt a field value."""
    return field_encryption.encrypt(value)


def decrypt_field(value):
    """Convenience function to decrypt a field value."""
    return field_encryption.decrypt(value)


# =============================================================================
# INPUT VALIDATION
# =============================================================================

class InputValidator:
    """
    Validates and sanitizes user input to prevent injection attacks.
    """

    # Patterns for validation
    PATTERNS = {
        'national_id': r'^[A-Za-z0-9-]{5,20}$',  # Alphanumeric with dashes
        'phone': r'^\+?[0-9]{10,15}$',  # International phone format
        'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        'name': r'^[a-zA-Z\s\'-]{2,100}$',  # Names with spaces, apostrophes, hyphens
        'alphanumeric': r'^[a-zA-Z0-9\s]+$',
        'numeric': r'^[0-9]+$',
    }

    # Dangerous patterns to detect injection attempts
    DANGEROUS_PATTERNS = [
        r'<script',
        r'javascript:',
        r'on\w+\s*=',
        r'SELECT\s+.*\s+FROM',
        r'INSERT\s+INTO',
        r'DELETE\s+FROM',
        r'DROP\s+TABLE',
        r'UNION\s+SELECT',
        r'--\s*$',
        r'/\*.*\*/',
    ]

    @classmethod
    def validate(cls, value, pattern_name, required=True):
        """
        Validate a value against a named pattern.
        Returns (is_valid, error_message).
        """
        if not value:
            if required:
                return False, "This field is required."
            return True, None

        value = str(value).strip()

        # Check for dangerous patterns
        if cls.contains_dangerous_input(value):
            security_logger.warning(f"Dangerous input detected: {value[:50]}...")
            return False, "Invalid characters detected."

        # Validate against pattern
        pattern = cls.PATTERNS.get(pattern_name)
        if pattern and not re.match(pattern, value):
            return False, f"Invalid format for {pattern_name}."

        return True, None

    @classmethod
    def contains_dangerous_input(cls, value):
        """Check if input contains potentially dangerous patterns."""
        value_lower = value.lower()
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return True
        return False

    @classmethod
    def sanitize_html(cls, value):
        """Remove HTML tags from input."""
        if not value:
            return value
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', '', str(value))
        # Escape remaining special characters
        clean = clean.replace('&', '&amp;')
        clean = clean.replace('<', '&lt;')
        clean = clean.replace('>', '&gt;')
        clean = clean.replace('"', '&quot;')
        clean = clean.replace("'", '&#x27;')
        return clean

    @classmethod
    def sanitize_for_log(cls, value, max_length=100):
        """Sanitize a value for safe logging."""
        if not value:
            return value
        value = str(value)[:max_length]
        # Remove newlines and control characters
        value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)
        return value


# =============================================================================
# ACCESS CONTROL DECORATORS
# =============================================================================

def require_role(*allowed_roles):
    """
    Decorator to restrict view access to specific user roles.
    Usage: @require_role('admin', 'doctor')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'Authentication required'}, status=401)

            user_role = getattr(request.user, 'role', None)
            if user_role not in allowed_roles:
                security_logger.warning(
                    f"Access denied: user={request.user.email}, "
                    f"role={user_role}, required={allowed_roles}, "
                    f"path={request.path}"
                )
                raise PermissionDenied("You don't have permission to access this resource.")

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_same_user_or_role(*allowed_roles):
    """
    Decorator to ensure user can only access their own data,
    unless they have one of the allowed roles.
    Expects 'user_id' or 'patient_id' in kwargs.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'Authentication required'}, status=401)

            user_role = getattr(request.user, 'role', None)

            # Check if user has privileged role
            if user_role in allowed_roles:
                return view_func(request, *args, **kwargs)

            # Check if accessing own data
            target_user_id = kwargs.get('user_id') or kwargs.get('pk')
            target_patient_id = kwargs.get('patient_id')

            if target_user_id and str(request.user.id) != str(target_user_id):
                security_logger.warning(
                    f"Unauthorized access attempt: user={request.user.id} "
                    f"tried to access user_id={target_user_id}"
                )
                raise PermissionDenied("You can only access your own data.")

            if target_patient_id:
                # Check if patient belongs to user
                from apps.patients.models import Patient
                try:
                    patient = Patient.objects.get(pk=target_patient_id)
                    if patient.user_id != request.user.id:
                        security_logger.warning(
                            f"Unauthorized patient access: user={request.user.id} "
                            f"tried to access patient_id={target_patient_id}"
                        )
                        raise PermissionDenied("You can only access your own records.")
                except Patient.DoesNotExist:
                    pass

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def api_csrf_protect(view_func):
    """
    CSRF protection decorator for API endpoints that accept both
    form data and JSON. For JSON requests, requires X-CSRFToken header.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # For GET requests, no CSRF check needed
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return view_func(request, *args, **kwargs)

        # Check for CSRF token in header for JSON requests
        content_type = request.content_type or ''
        if 'application/json' in content_type:
            csrf_token = request.META.get('HTTP_X_CSRFTOKEN', '')
            if not csrf_token:
                return JsonResponse(
                    {'error': 'CSRF token missing. Include X-CSRFToken header.'},
                    status=403
                )

        # Use Django's CSRF protection
        return csrf_protect(view_func)(request, *args, **kwargs)

    return wrapper


def log_data_access(resource_type):
    """
    Decorator to log access to sensitive data for audit purposes.
    Usage: @log_data_access('patient_record')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            response = view_func(request, *args, **kwargs)

            # Log successful data access
            if response.status_code == 200:
                security_logger.info(
                    f"Data access: user={request.user.email if request.user.is_authenticated else 'anonymous'}, "
                    f"resource={resource_type}, "
                    f"path={request.path}, "
                    f"ip={request.META.get('REMOTE_ADDR')}"
                )

            return response
        return wrapper
    return decorator


# =============================================================================
# SECURE COMPARISON
# =============================================================================

def secure_compare(val1, val2):
    """
    Compare two values in constant time to prevent timing attacks.
    """
    if len(val1) != len(val2):
        return False
    return hmac.compare_digest(val1, val2)


# =============================================================================
# PASSWORD STRENGTH CHECKER
# =============================================================================

def check_password_strength(password):
    """
    Check password strength for healthcare compliance.
    Returns (is_strong, list_of_issues).
    """
    issues = []

    if len(password) < 12:
        issues.append("Password must be at least 12 characters long")

    if not re.search(r'[A-Z]', password):
        issues.append("Password must contain at least one uppercase letter")

    if not re.search(r'[a-z]', password):
        issues.append("Password must contain at least one lowercase letter")

    if not re.search(r'[0-9]', password):
        issues.append("Password must contain at least one number")

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        issues.append("Password must contain at least one special character")

    # Check for common patterns
    common_patterns = ['password', '123456', 'qwerty', 'admin', 'hospital']
    for pattern in common_patterns:
        if pattern.lower() in password.lower():
            issues.append(f"Password must not contain common words like '{pattern}'")

    return len(issues) == 0, issues
