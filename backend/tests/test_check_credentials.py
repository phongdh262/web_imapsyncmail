import pytest
import os
import sys
from unittest.mock import patch, MagicMock

# Thêm đường dẫn tới thư mục backend để module có thể import các file chính xác
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from check_credentials import detect_provider, check_imap_login, check_bulk
import socket
import imaplib

def test_detect_provider():
    """Verify IMAP server detection based on common domains."""
    gmail_case = detect_provider("user@gmail.com")
    assert gmail_case["host"] == "imap.gmail.com"
    assert gmail_case["name"] == "Gmail"
    
    yandex_case = detect_provider("test@yandex.ru")
    assert yandex_case["host"] == "imap.yandex.com"
    assert yandex_case["name"] == "Yandex"
    
    outlook_case = detect_provider("abc@outlook.com")
    assert outlook_case["host"] == "outlook.office365.com"
    
    # Custom/unsupported domain
    unknown_case = detect_provider("user@unsupporteddomain.xyz")
    assert unknown_case is None

def test_detect_provider_edge_cases():
    """Verify edge cases for email detection string parsing."""
    case1 = detect_provider("USER@GMAIL.COM")
    assert case1["host"] == "imap.gmail.com"
    
    case2 = detect_provider("  test@yahoo.com  ")
    assert case2["host"] == "imap.mail.yahoo.com"
    
@patch('check_credentials.imaplib.IMAP4_SSL')
def test_check_imap_login_success(mock_imap):
    """Simulate successful IMAP login."""
    # Setup the mock
    mock_instance = MagicMock()
    mock_imap.return_value = mock_instance
    
    result = check_imap_login("user@gmail.com", "password123")
    
    # Assert return format
    assert result["status"] == "success"
    assert result["provider"] == "Gmail"
    assert "successful" in result["message"].lower()
    
    # Verify mock interactions
    mock_imap.assert_called_once()
    mock_instance.login.assert_called_with("user@gmail.com", "password123")
    mock_instance.logout.assert_called_once()

@patch('check_credentials.imaplib.IMAP4_SSL')
def test_check_imap_login_auth_fail(mock_imap):
    """Simulate authentication failure."""
    # Setup the mock to raise IMAP4.error when logging in
    mock_instance = MagicMock()
    mock_instance.login.side_effect = imaplib.IMAP4.error("AUTHENTICATIONFAILED")
    mock_imap.return_value = mock_instance
    
    result = check_imap_login("user@yandex.com", "wrongpass")
    
    assert result["status"] == "failed"
    assert "Authentication failed" in result["message"]

@patch('check_credentials.imaplib.IMAP4_SSL')
def test_check_imap_login_timeout(mock_imap):
    """Simulate connection timeout to IMAP server."""
    # Setup mock to raise socket.timeout
    mock_imap.side_effect = socket.timeout("timeout check")
    
    result = check_imap_login("user@outlook.com", "pass")
    
    assert result["status"] == "failed"
    assert "timed out" in result["message"].lower()

@patch('check_credentials.check_imap_login')
def test_check_bulk(mock_check_imap_login):
    """Test concurrent checking functionality."""
    # Mock individual checks
    def side_effect(email, password, host, port):
        if "fail" in email:
            return {"email": email, "status": "failed", "message": "Failed test"}
        return {"email": email, "status": "success", "message": "OK"}
        
    mock_check_imap_login.side_effect = side_effect
    
    credentials = [
        {"email": "good@gmail.com", "password": "pass"},
        {"email": "fail@yandex.com", "password": "pass"}
    ]
    
    results = check_bulk(credentials)
    
    assert len(results) == 2
    assert results[0]["email"] == "good@gmail.com"
    assert results[0]["status"] == "success"
    
    assert results[1]["email"] == "fail@yandex.com"
    assert results[1]["status"] == "failed"
