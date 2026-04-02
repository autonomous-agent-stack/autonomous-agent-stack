"""
Simple lead capture form with email and phone validation.
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class Lead:
    """Represents a captured lead."""
    name: str
    email: str
    phone: Optional[str] = None
    
    def __post_init__(self):
        # Strip whitespace
        self.name = self.name.strip()
        self.email = self.email.strip()
        if self.phone:
            self.phone = self.phone.strip()


def validate_email(email: str) -> bool:
    """Validate email format using a simple regex pattern."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """Validate phone number (accepts various formats)."""
    # Remove common separators and check for 10+ digits
    cleaned = re.sub(r'[\s\-\(\)\+]', '', phone)
    return cleaned.isdigit() and len(cleaned) >= 10


def validate_lead(lead: Lead) -> tuple[bool, list[str]]:
    """
    Validate a lead and return (is_valid, list_of_errors).
    """
    errors = []
    
    if not lead.name:
        errors.append("Name is required")
    
    if not lead.email:
        errors.append("Email is required")
    elif not validate_email(lead.email):
        errors.append("Invalid email format")
    
    if lead.phone and not validate_phone(lead.phone):
        errors.append("Invalid phone number format")
    
    return len(errors) == 0, errors


def capture_lead(name: str, email: str, phone: Optional[str] = None) -> tuple[bool, str]:
    """
    Capture and validate a lead.
    
    Returns (success, message).
    """
    lead = Lead(name=name, email=email, phone=phone)
    is_valid, errors = validate_lead(lead)
    
    if is_valid:
        # In a real app, this would save to a database
        return True, f"Lead captured: {lead.name} ({lead.email})"
    else:
        return False, f"Validation failed: {'; '.join(errors)}"


# Tiny validation test
if __name__ == "__main__":
    # Test email validation
    assert validate_email("test@example.com") == True
    assert validate_email("invalid-email") == False
    assert validate_email("user@domain") == False
    
    # Test phone validation
    assert validate_phone("555-123-4567") == True
    assert validate_phone("(555) 123-4567") == True
    assert validate_phone("+1 555 123 4567") == True
    assert validate_phone("123") == False
    
    # Test lead validation
    valid_lead = Lead(name="John Doe", email="john@example.com")
    is_valid, errors = validate_lead(valid_lead)
    assert is_valid == True
    assert errors == []
    
    invalid_lead = Lead(name="", email="bad-email")
    is_valid, errors = validate_lead(invalid_lead)
    assert is_valid == False
    assert "Name is required" in errors
    assert "Invalid email format" in errors
    
    # Test capture function
    success, msg = capture_lead("Jane Smith", "jane@example.com", "555-123-4567")
    assert success == True
    assert "Jane Smith" in msg
    
    success, msg = capture_lead("", "invalid", "123")
    assert success == False
    assert "Validation failed" in msg
    
    print("✅ All validation tests passed!")
