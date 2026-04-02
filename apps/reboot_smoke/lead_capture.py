"""
Minimal lead capture with email validation and tiny test.
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class Lead:
    """A captured lead."""
    name: str
    email: str
    phone: Optional[str] = None


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_lead(lead: Lead) -> tuple[bool, list[str]]:
    """Validate a lead. Returns (is_valid, errors)."""
    errors = []
    if not lead.name.strip():
        errors.append("Name required")
    if not lead.email.strip():
        errors.append("Email required")
    elif not validate_email(lead.email):
        errors.append("Invalid email")
    return len(errors) == 0, errors


if __name__ == "__main__":
    # Tiny validation test
    assert validate_email("test@example.com") == True
    assert validate_email("bad") == False

    lead = Lead(name="Test User", email="test@example.com")
    is_valid, errors = validate_lead(lead)
    assert is_valid == True
    assert errors == []

    bad_lead = Lead(name="", email="invalid")
    is_valid, errors = validate_lead(bad_lead)
    assert is_valid == False
    assert "Name required" in errors
    assert "Invalid email" in errors

    print("✅ Tiny validation test passed!")
