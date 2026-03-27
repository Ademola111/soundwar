"""
Security Utilities
"""
import re
import bleach


def sanitize_input(value: str) -> str:
    """Sanitize user input to prevent XSS and injection attacks"""
    if not isinstance(value, str):
        return ''
    
    # Remove HTML tags
    cleaned = bleach.clean(value, tags=[], strip=True)
    
    # Limit length
    cleaned = cleaned[:1000]
    
    return cleaned.strip()


def validate_email(email: str) -> bool:
    """Validate email format"""
    if not email or not isinstance(email, str):
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_password(password: str) -> tuple:
    """
    Validate password strength
    Returns: (is_valid: bool, message: str)
    """
    if not password or not isinstance(password, str):
        return False, 'Password is required'
    
    if len(password) < 8:
        return False, 'Password must be at least 8 characters'
    
    if not re.search(r'[A-Z]', password):
        return False, 'Password must contain an uppercase letter'
    
    if not re.search(r'[a-z]', password):
        return False, 'Password must contain a lowercase letter'
    
    if not re.search(r'[0-9]', password):
        return False, 'Password must contain a number'
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, 'Password must contain a special character'
    
    return True, 'Valid'


def validate_transaction_ref(ref: str) -> bool:
    """Validate Flutterwave transaction reference"""
    if not ref or not isinstance(ref, str):
        return False
    
    pattern = r'^[a-zA-Z0-9_-]+$'
    return bool(re.match(pattern, ref)) and 10 <= len(ref) <= 100


def validate_username(username: str) -> tuple:
    """
    Validate username format
    Returns: (is_valid: bool, message: str)
    """
    if not username or not isinstance(username, str):
        return False, 'Username is required'
    
    if len(username) < 3:
        return False, 'Username must be at least 3 characters'
    
    if len(username) > 30:
        return False, 'Username must be at most 30 characters'
    
    pattern = r'^[a-zA-Z0-9_]+$'
    if not re.match(pattern, username):
        return False, 'Username can only contain letters, numbers, and underscores'
    
    return True, 'Valid'
