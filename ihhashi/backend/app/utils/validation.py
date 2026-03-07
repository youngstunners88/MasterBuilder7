"""
Enhanced validation utilities for iHhashi
Includes input sanitization, ID validation, and security checks
"""

import re
import html
from typing import Optional
from bson import ObjectId
from bson.errors import InvalidId
import bleach


# South Africa coordinate bounds
SA_BOUNDS = {
    "lat_min": -35.0,
    "lat_max": -22.0,
    "lng_min": 16.0,
    "lng_max": 33.0
}


def safe_object_id(id_str: str) -> Optional[ObjectId]:
    """
    Safely convert string to ObjectId.
    Returns None if invalid.
    """
    if not id_str:
        return None
    try:
        # Validate format before conversion
        if not isinstance(id_str, str):
            return None
        # Check for valid ObjectId pattern (24 hex chars)
        if not re.match(r'^[a-fA-F0-9]{24}$', id_str):
            return None
        return ObjectId(id_str)
    except (InvalidId, TypeError, ValueError):
        return None


def sanitize_html_content(content: Optional[str], max_length: int = 1000) -> Optional[str]:
    """
    Sanitize HTML content using bleach library.
    Removes all HTML tags and returns plain text.
    
    Args:
        content: Raw input string
        max_length: Maximum allowed length
        
    Returns:
        Sanitized plain text or None
    """
    if not content:
        return None
    
    # First, escape HTML entities
    text = html.escape(content)
    
    # Use bleach to strip any remaining HTML-like content
    # This handles cases where HTML entities were decoded
    text = bleach.clean(text, tags=[], strip=True)
    
    # Remove any remaining HTML-like patterns
    text = re.sub(r'<[^>]+>', '', text)
    
    # Normalize whitespace
    text = ' '.join(text.split())
    
    # Truncate to max length
    if len(text) > max_length:
        text = text[:max_length].rsplit(' ', 1)[0] + '...'
    
    return text.strip()


def validate_sa_phone(phone: str) -> Optional[str]:
    """
    Validate and normalize South African phone number.
    
    Args:
        phone: Phone number string
        
    Returns:
        Normalized phone number in format +27XXXXXXXXX or None
    """
    if not phone:
        return None
    
    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone)
    
    # Handle different formats
    if cleaned.startswith('+27'):
        # Already in correct format
        if len(cleaned) != 12:
            return None
        return cleaned
    elif cleaned.startswith('0'):
        # Convert 0XX to +27XX
        if len(cleaned) != 10:
            return None
        return '+27' + cleaned[1:]
    elif cleaned.startswith('27') and len(cleaned) == 11:
        # Missing + prefix
        return '+' + cleaned
    
    return None


def validate_sa_coordinates(lat: float, lng: float) -> bool:
    """
    Validate coordinates are within South Africa bounds.
    
    Args:
        lat: Latitude
        lng: Longitude
        
    Returns:
        True if within SA bounds
    """
    try:
        lat = float(lat)
        lng = float(lng)
    except (TypeError, ValueError):
        return False
    
    return (
        SA_BOUNDS["lat_min"] <= lat <= SA_BOUNDS["lat_max"] and
        SA_BOUNDS["lng_min"] <= lng <= SA_BOUNDS["lng_max"]
    )


def validate_referral_code(code: str) -> bool:
    """
    Validate referral code format.
    Prevents NoSQL injection attempts.
    
    Args:
        code: Referral code string
        
    Returns:
        True if valid format
    """
    if not code or not isinstance(code, str):
        return False
    
    # Only allow alphanumeric and hyphens
    # Format: IH-C-XXXXXX or IH-V-XXXXXX
    pattern = r'^[A-Z]{2}-[CV]-[A-Z0-9]{6,10}$'
    return bool(re.match(pattern, code.upper()))


def validate_bank_account_number(account_number: str) -> bool:
    """
    Validate South African bank account number.
    
    Args:
        account_number: Account number string
        
    Returns:
        True if valid format
    """
    if not account_number:
        return False
    
    # Remove spaces and dashes
    cleaned = re.sub(r'[\s-]', '', account_number)
    
    # SA account numbers are typically 9-13 digits
    if not cleaned.isdigit():
        return False
    
    return 9 <= len(cleaned) <= 13


def validate_order_notes(notes: Optional[str]) -> Optional[str]:
    """
    Validate and sanitize order notes.
    
    Args:
        notes: Raw notes string
        
    Returns:
        Sanitized notes or None
    """
    return sanitize_html_content(notes, max_length=500)


def is_nosql_injection_attempt(value: str) -> bool:
    """
    Check if string contains potential NoSQL injection patterns.
    
    Args:
        value: String to check
        
    Returns:
        True if suspicious patterns found
    """
    if not isinstance(value, str):
        return False
    
    # Patterns commonly used in NoSQL injection
    suspicious_patterns = [
        r'\$where',
        r'\$ne',
        r'\$gt',
        r'\$lt',
        r'\$regex',
        r'\$exists',
        r'\$or',
        r'\$and',
        r'__proto__',
        r'constructor',
    ]
    
    value_lower = value.lower()
    for pattern in suspicious_patterns:
        if re.search(pattern, value_lower):
            return True
    
    return False


def sanitize_search_query(query: str, max_length: int = 100) -> Optional[str]:
    """
    Sanitize search query input.
    
    Args:
        query: Search query string
        max_length: Maximum allowed length
        
    Returns:
        Sanitized query or None
    """
    if not query:
        return None
    
    # Remove special MongoDB characters
    query = re.sub(r'[${}()[\]]', '', query)
    
    # Normalize whitespace
    query = ' '.join(query.split())
    
    # Truncate
    if len(query) > max_length:
        query = query[:max_length]
    
    return query.strip()


def validate_email_domain(email: str, allowed_domains: Optional[list] = None) -> bool:
    """
    Validate email domain is not from disposable email provider.
    
    Args:
        email: Email address
        allowed_domains: Optional list of allowed domains
        
    Returns:
        True if email domain is acceptable
    """
    if not email or '@' not in email:
        return False
    
    domain = email.split('@')[1].lower()
    
    # Common disposable email domains
    disposable_domains = {
        'tempmail.com', 'throwaway.com', 'mailinator.com',
        'guerrillamail.com', 'sharklasers.com', 'yopmail.com'
    }
    
    if domain in disposable_domains:
        return False
    
    if allowed_domains and domain not in allowed_domains:
        return False
    
    return True


def calculate_password_strength(password: str) -> dict:
    """
    Calculate password strength score.
    
    Args:
        password: Password string
        
    Returns:
        Dict with score and feedback
    """
    score = 0
    feedback = []
    
    if len(password) >= 8:
        score += 1
    else:
        feedback.append("Password must be at least 8 characters")
    
    if len(password) >= 12:
        score += 1
    
    if re.search(r'[A-Z]', password):
        score += 1
    else:
        feedback.append("Add uppercase letters")
    
    if re.search(r'[a-z]', password):
        score += 1
    else:
        feedback.append("Add lowercase letters")
    
    if re.search(r'\d', password):
        score += 1
    else:
        feedback.append("Add numbers")
    
    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        score += 1
    else:
        feedback.append("Add special characters")
    
    # Check for common patterns
    common_patterns = ['123', 'abc', 'password', 'qwerty', 'admin']
    if any(pattern in password.lower() for pattern in common_patterns):
        score -= 2
        feedback.append("Avoid common patterns")
    
    return {
        "score": max(0, score),
        "max_score": 6,
        "is_strong": score >= 4,
        "feedback": feedback
    }
"""
Enhanced validation utilities for iHhashi
Includes input sanitization, ID validation, and security checks
"""

import re
import html
from typing import Optional
from bson import ObjectId
from bson.errors import InvalidId
import bleach


# South Africa coordinate bounds
SA_BOUNDS = {
    "lat_min": -35.0,
    "lat_max": -22.0,
    "lng_min": 16.0,
    "lng_max": 33.0
}


def safe_object_id(id_str: str) -> Optional[ObjectId]:
    """
    Safely convert string to ObjectId.
    Returns None if invalid.
    """
    if not id_str:
        return None
    try:
        # Validate format before conversion
        if not isinstance(id_str, str):
            return None
        # Check for valid ObjectId pattern (24 hex chars)
        if not re.match(r'^[a-fA-F0-9]{24}$', id_str):
            return None
        return ObjectId(id_str)
    except (InvalidId, TypeError, ValueError):
        return None


def sanitize_html_content(content: Optional[str], max_length: int = 1000) -> Optional[str]:
    """
    Sanitize HTML content using bleach library.
    Removes all HTML tags and returns plain text.
    
    Args:
        content: Raw input string
        max_length: Maximum allowed length
        
    Returns:
        Sanitized plain text or None
    """
    if not content:
        return None
    
    # First, escape HTML entities
    text = html.escape(content)
    
    # Use bleach to strip any remaining HTML-like content
    # This handles cases where HTML entities were decoded
    text = bleach.clean(text, tags=[], strip=True)
    
    # Remove any remaining HTML-like patterns
    text = re.sub(r'<[^>]+>', '', text)
    
    # Normalize whitespace
    text = ' '.join(text.split())
    
    # Truncate to max length
    if len(text) > max_length:
        text = text[:max_length].rsplit(' ', 1)[0] + '...'
    
    return text.strip()


def validate_sa_phone(phone: str) -> Optional[str]:
    """
    Validate and normalize South African phone number.
    
    Args:
        phone: Phone number string
        
    Returns:
        Normalized phone number in format +27XXXXXXXXX or None
    """
    if not phone:
        return None
    
    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone)
    
    # Handle different formats
    if cleaned.startswith('+27'):
        # Already in correct format
        if len(cleaned) != 12:
            return None
        return cleaned
    elif cleaned.startswith('0'):
        # Convert 0XX to +27XX
        if len(cleaned) != 10:
            return None
        return '+27' + cleaned[1:]
    elif cleaned.startswith('27') and len(cleaned) == 11:
        # Missing + prefix
        return '+' + cleaned
    
    return None


def validate_sa_coordinates(lat: float, lng: float) -> bool:
    """
    Validate coordinates are within South Africa bounds.
    
    Args:
        lat: Latitude
        lng: Longitude
        
    Returns:
        True if within SA bounds
    """
    try:
        lat = float(lat)
        lng = float(lng)
    except (TypeError, ValueError):
        return False
    
    return (
        SA_BOUNDS["lat_min"] <= lat <= SA_BOUNDS["lat_max"] and
        SA_BOUNDS["lng_min"] <= lng <= SA_BOUNDS["lng_max"]
    )


def validate_referral_code(code: str) -> bool:
    """
    Validate referral code format.
    Prevents NoSQL injection attempts.
    
    Args:
        code: Referral code string
        
    Returns:
        True if valid format
    """
    if not code or not isinstance(code, str):
        return False
    
    # Only allow alphanumeric and hyphens
    # Format: IH-C-XXXXXX or IH-V-XXXXXX
    pattern = r'^[A-Z]{2}-[CV]-[A-Z0-9]{6,10}$'
    return bool(re.match(pattern, code.upper()))


def validate_bank_account_number(account_number: str) -> bool:
    """
    Validate South African bank account number.
    
    Args:
        account_number: Account number string
        
    Returns:
        True if valid format
    """
    if not account_number:
        return False
    
    # Remove spaces and dashes
    cleaned = re.sub(r'[\s-]', '', account_number)
    
    # SA account numbers are typically 9-13 digits
    if not cleaned.isdigit():
        return False
    
    return 9 <= len(cleaned) <= 13


def validate_order_notes(notes: Optional[str]) -> Optional[str]:
    """
    Validate and sanitize order notes.
    
    Args:
        notes: Raw notes string
        
    Returns:
        Sanitized notes or None
    """
    return sanitize_html_content(notes, max_length=500)


def is_nosql_injection_attempt(value: str) -> bool:
    """
    Check if string contains potential NoSQL injection patterns.
    
    Args:
        value: String to check
        
    Returns:
        True if suspicious patterns found
    """
    if not isinstance(value, str):
        return False
    
    # Patterns commonly used in NoSQL injection
    suspicious_patterns = [
        r'\$where',
        r'\$ne',
        r'\$gt',
        r'\$lt',
        r'\$regex',
        r'\$exists',
        r'\$or',
        r'\$and',
        r'__proto__',
        r'constructor',
    ]
    
    value_lower = value.lower()
    for pattern in suspicious_patterns:
        if re.search(pattern, value_lower):
            return True
    
    return False


def sanitize_search_query(query: str, max_length: int = 100) -> Optional[str]:
    """
    Sanitize search query input.
    
    Args:
        query: Search query string
        max_length: Maximum allowed length
        
    Returns:
        Sanitized query or None
    """
    if not query:
        return None
    
    # Remove special MongoDB characters
    query = re.sub(r'[${}()[\]]', '', query)
    
    # Normalize whitespace
    query = ' '.join(query.split())
    
    # Truncate
    if len(query) > max_length:
        query = query[:max_length]
    
    return query.strip()


def validate_email_domain(email: str, allowed_domains: Optional[list] = None) -> bool:
    """
    Validate email domain is not from disposable email provider.
    
    Args:
        email: Email address
        allowed_domains: Optional list of allowed domains
        
    Returns:
        True if email domain is acceptable
    """
    if not email or '@' not in email:
        return False
    
    domain = email.split('@')[1].lower()
    
    # Common disposable email domains
    disposable_domains = {
        'tempmail.com', 'throwaway.com', 'mailinator.com',
        'guerrillamail.com', 'sharklasers.com', 'yopmail.com'
    }
    
    if domain in disposable_domains:
        return False
    
    if allowed_domains and domain not in allowed_domains:
        return False
    
    return True


def calculate_password_strength(password: str) -> dict:
    """
    Calculate password strength score.
    
    Args:
        password: Password string
        
    Returns:
        Dict with score and feedback
    """
    score = 0
    feedback = []
    
    if len(password) >= 8:
        score += 1
    else:
        feedback.append("Password must be at least 8 characters")
    
    if len(password) >= 12:
        score += 1
    
    if re.search(r'[A-Z]', password):
        score += 1
    else:
        feedback.append("Add uppercase letters")
    
    if re.search(r'[a-z]', password):
        score += 1
    else:
        feedback.append("Add lowercase letters")
    
    if re.search(r'\d', password):
        score += 1
    else:
        feedback.append("Add numbers")
    
    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        score += 1
    else:
        feedback.append("Add special characters")
    
    # Check for common patterns
    common_patterns = ['123', 'abc', 'password', 'qwerty', 'admin']
    if any(pattern in password.lower() for pattern in common_patterns):
        score -= 2
        feedback.append("Avoid common patterns")
    
    return {
        "score": max(0, score),
        "max_score": 6,
        "is_strong": score >= 4,
        "feedback": feedback
    }
