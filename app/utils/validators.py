import re
from email_validator import validate_email as email_validator, EmailNotValidError

def validate_email(email):
    """Validate email address"""
    try:
        email_validator(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False

def validate_phone(phone):
    """Validate Kenyan phone number"""
    # Remove spaces and dashes
    phone = re.sub(r'[\s\-]', '', phone)
    
    # Check for Kenyan format
    # Valid formats: +254XXXXXXXXX, 254XXXXXXXXX, 07XXXXXXXX, 01XXXXXXXX
    patterns = [
        r'^\+254[17]\d{8}$',
        r'^254[17]\d{8}$',
        r'^0[17]\d{8}$',
    ]
    
    return any(re.match(pattern, phone) for pattern in patterns)

def validate_password(password):
    """Validate password strength"""
    if not password:
        return False
    
    # Minimum 8 characters
    if len(password) < 8:
        return False
    
    return True

def validate_id_number(id_number):
    """Validate Kenyan ID number"""
    # Kenyan ID numbers are 8 digits
    return bool(re.match(r'^\d{8}$', id_number))

def format_phone_number(phone):
    """Format phone number to standard format (+254XXXXXXXXX)"""
    # Remove spaces and dashes
    phone = re.sub(r'[\s\-]', '', phone)
    
    # Convert to international format
    if phone.startswith('0'):
        phone = '+254' + phone[1:]
    elif phone.startswith('254'):
        phone = '+' + phone
    
    return phone
