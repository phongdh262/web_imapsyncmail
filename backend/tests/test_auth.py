import pytest
import os
import sys

# Thêm đường dẫn tới thư mục backend để module có thể import các file chính xác
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_csrf_token,
    SECRET_KEY,
    ALGORITHM
)
from jose import jwt

def test_password_hashing():
    """Verify that password hashing and checking works correctly."""
    plain_password = "super_secure_password_123!"
    hashed_password = get_password_hash(plain_password)
    
    # Hash requires salt, so the hash shouldn't be the same as plain password
    assert plain_password != hashed_password
    
    # Verification should pass for the correct password
    assert verify_password(plain_password, hashed_password) is True
    
    # Verification should fail for incorrect password
    assert verify_password("wrong_password", hashed_password) is False

def test_password_hashing_unicode():
    """Verify password hashing with special unicode characters."""
    plain_password = "mật_khẩu_tiếng_việt_🌟"
    hashed_password = get_password_hash(plain_password)
    assert verify_password(plain_password, hashed_password) is True

def test_password_hashing_long_password():
    """Verify password hashing with very long passwords (>72 chars).
    Bcrypt normally fails or truncates, but our pre-hashing ensures it works perfectly.
    """
    long_pass = "a" * 100
    hashed_password = get_password_hash(long_pass)
    assert verify_password(long_pass, hashed_password) is True
    assert verify_password("a" * 99, hashed_password) is False

def test_create_access_token():
    """Verify JWT access token creation."""
    data = {"sub": "admin_user"}
    token = create_access_token(data)
    
    # Should return a string that can be decoded
    assert isinstance(token, str)
    
    # Verify the decoded payload
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload.get("sub") == "admin_user"
    assert "exp" in payload  # Ensure expiration is set

def test_create_csrf_token():
    """Verify CSRF token generation returns valid urlsafe string."""
    token = create_csrf_token()
    assert isinstance(token, str)
    assert len(token) > 20  # Should be sufficiently long
