"""
Utility helper functions
"""
import random
import string
import re
from datetime import datetime, timedelta


def generate_unique_id(prefix, length=10):
    """
    Generate a unique ID with a prefix
    
    Args:
        prefix (str): Prefix for the ID (e.g., 'QP', 'TXN')
        length (int): Length of random part
    
    Returns:
        str: Unique ID like 'QP-ABC123XYZ'
    """
    chars = string.ascii_uppercase + string.digits
    random_part = ''.join(random.choices(chars, k=length))
    return f"{prefix}-{random_part}"


def calculate_fee(amount, fee_rate=0.015):
    """
    Calculate transaction fee
    
    Args:
        amount (float): Transaction amount
        fee_rate (float): Fee rate (default 1.5%)
    
    Returns:
        float: Calculated fee rounded to 2 decimal places
    """
    return round(amount * fee_rate, 2)


def validate_email(email):
    """
    Validate email format
    
    Args:
        email (str): Email to validate
    
    Returns:
        bool: True if valid, False otherwise
    """
    if not isinstance(email, str) or not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email, re.IGNORECASE) is not None


def validate_phone(phone):
    """
    Validate phone number format
    
    Args:
        phone (str): Phone number to validate
    
    Returns:
        bool: True if valid, False otherwise
    """
    if not phone:
        return True  # Phone is optional
    
    # Remove spaces, dashes, and parentheses
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    # Check if it's a valid phone number (8-15 digits with optional + prefix)
    pattern = r'^\+?[0-9]{8,15}$'
    return re.match(pattern, cleaned) is not None


def format_currency(amount, currency='USD'):
    """
    Format amount as currency
    
    Args:
        amount (float): Amount to format
        currency (str): Currency code
    
    Returns:
        str: Formatted currency string
    """
    symbols = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'KES': 'KSh'
    }
    symbol = symbols.get(currency, currency)
    return f"{symbol}{amount:,.2f}"


def validate_transaction_amount(amount, min_amount=1.0, max_amount=10000.0):
    """
    Validate transaction amount
    
    Args:
        amount (float): Amount to validate
        min_amount (float): Minimum allowed amount
        max_amount (float): Maximum allowed amount
    
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return False, "Invalid amount format"
    
    if amount < min_amount:
        return False, f"Amount must be at least ${min_amount}"
    if amount > max_amount:
        return False, f"Amount cannot exceed ${max_amount}"
    return True, None


def sanitize_input(text):
    """
    Sanitize user input to prevent XSS
    
    Args:
        text (str): Text to sanitize
    
    Returns:
        str: Sanitized text
    """
    if not text:
        return text
    
    # Remove potentially harmful characters
    dangerous_chars = ['<', '>', '"', "'", '&']
    for char in dangerous_chars:
        text = text.replace(char, '')
    
    return text.strip()


def get_date_range(period='week'):
    """
    Get start and end dates for a period
    
    Args:
        period (str): 'day', 'week', 'month', 'year'
    
    Returns:
        tuple: (start_date, end_date)
    """
    end_date = datetime.utcnow()
    
    if period == 'day':
        start_date = end_date - timedelta(days=1)
    elif period == 'week':
        start_date = end_date - timedelta(weeks=1)
    elif period == 'month':
        start_date = end_date - timedelta(days=30)
    elif period == 'year':
        start_date = end_date - timedelta(days=365)
    else:
        start_date = end_date - timedelta(weeks=1)
    
    return start_date, end_date


def validate_password_strength(password):
    """
    Validate password strength
    
    Args:
        password (str): Password to validate
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
    
    return True, None


class ValidationError(Exception):
    """Custom validation error"""
    pass


class InsufficientFundsError(Exception):
    """Custom insufficient funds error"""
    pass


class UnauthorizedError(Exception):
    """Custom unauthorized error"""
    pass