import pytest
from agent_service.core.security import SecurityManager

def test_presidio_redaction():
    sec = SecurityManager.get_instance()
    
    # 1. Email and Phone
    text = "Contact alice@example.com at 555-0199."
    clean = sec.sanitize_input(text)
    assert "<EMAIL_REDACTED>" in clean
    assert "<PHONE_REDACTED>" in clean
    
    # 2. Contextual Logic (Presidio strength vs Regex)
    # Regex often catches "2023" as a phone number part. Presidio shouldn't.
    text_context = "The year is 2023 and my IP is 192.168.1.1"
    clean_context = sec.sanitize_input(text_context)
    
    assert "2023" in clean_context # Should NOT be redacted
    assert "<REDACTED>" in clean_context or "<IP_ADDRESS>" in clean_context # IP should be redacted

if __name__ == "__main__":
    test_presidio_redaction()