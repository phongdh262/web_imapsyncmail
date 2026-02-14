"""
test_auth_extended.py
Authentication and JWT token tests for IMAP Sync Pro.
Tests cover login flow, token generation/validation, bcrypt hashing,
and admin auto-creation logic.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os
from datetime import timedelta, datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import app, get_db
from database import Base, User
from auth import (
    verify_password, get_password_hash, create_access_token,
    SECRET_KEY, ALGORITHM
)

# Setup test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_auth.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def create_test_user():
    """Create a test user in the database"""
    db = TestingSessionLocal()
    user = User(
        username="testadmin",
        hashed_password=get_password_hash("password123")
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user
    db.close()


# ==========================================
# 1. Login Endpoint Tests
# ==========================================

class TestLogin:
    """Tests for /api/login endpoint"""

    def test_login_success(self, create_test_user):
        """Successful login returns access token"""
        response = client.post("/api/login", data={
            "username": "testadmin",
            "password": "password123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0

    def test_login_wrong_password(self, create_test_user):
        """Login with incorrect password"""
        response = client.post("/api/login", data={
            "username": "testadmin",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    def test_login_nonexistent_user(self):
        """Login as non-existent user (not phongdh, no auto-create)"""
        response = client.post("/api/login", data={
            "username": "nobody",
            "password": "any"
        })
        assert response.status_code == 401

    def test_login_empty_credentials(self):
        """Login with empty username and password"""
        response = client.post("/api/login", data={
            "username": "",
            "password": ""
        })
        assert response.status_code in [401, 422]

    def test_login_missing_fields(self):
        """Login without providing required fields"""
        response = client.post("/api/login", data={})
        assert response.status_code == 422

    def test_auto_create_admin_user(self):
        """First login as 'phongdh' auto-creates the user"""
        admin_password = os.getenv("ADMIN_PASSWORD", "changeme123")
        response = client.post("/api/login", data={
            "username": "phongdh",
            "password": admin_password
        })
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_returns_bearer_token_type(self, create_test_user):
        """Token response includes 'bearer' type"""
        response = client.post("/api/login", data={
            "username": "testadmin",
            "password": "password123"
        })
        assert response.json()["token_type"] == "bearer"


# ==========================================
# 2. JWT Token Tests
# ==========================================

class TestJWTTokens:
    """Tests for JWT token creation and validation"""

    def test_token_creation(self):
        """Create a token and verify it's a valid string"""
        token = create_access_token(data={"sub": "testuser"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_with_expiration(self):
        """Create token with custom expiration"""
        token = create_access_token(
            data={"sub": "testuser"},
            expires_delta=timedelta(hours=2)
        )
        assert isinstance(token, str)

        # Decode and verify
        from jose import jwt
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "testuser"
        assert "exp" in payload

    def test_token_decode_valid(self):
        """Decode a valid token returns correct claims"""
        from jose import jwt
        token = create_access_token(data={"sub": "myuser"})
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "myuser"

    def test_token_expired(self):
        """Expired token raises error on decode"""
        from jose import jwt, JWTError
        token = create_access_token(
            data={"sub": "testuser"},
            expires_delta=timedelta(seconds=-10)  # Already expired
        )
        with pytest.raises(Exception):  # ExpiredSignatureError
            jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    def test_token_malformed(self):
        """Random string as token should fail"""
        from jose import jwt, JWTError
        with pytest.raises(JWTError):
            jwt.decode("not.a.valid.token", SECRET_KEY, algorithms=[ALGORITHM])

    def test_token_wrong_secret(self):
        """Token signed with wrong secret should fail"""
        from jose import jwt, JWTError
        token = create_access_token(data={"sub": "testuser"})
        with pytest.raises(JWTError):
            jwt.decode(token, "wrong-secret-key", algorithms=[ALGORITHM])

    def test_token_default_expiration(self):
        """Token without explicit expiration uses default (15 min)"""
        from jose import jwt
        token = create_access_token(data={"sub": "testuser"})
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Should have exp claim
        assert "exp" in payload


# ==========================================
# 3. Password Hashing Tests
# ==========================================

class TestPasswordHashing:
    """Tests for bcrypt password hashing functions"""

    def test_hash_then_verify(self):
        """Hash a password and verify it"""
        password = "testpassword123"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_hash_wrong_password(self):
        """Verify with wrong password returns False"""
        hashed = get_password_hash("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_different_hashes_for_same_password(self):
        """Same password produces different hashes (bcrypt salt)"""
        hash1 = get_password_hash("samepassword")
        hash2 = get_password_hash("samepassword")
        assert hash1 != hash2  # Different salts
        # But both should verify
        assert verify_password("samepassword", hash1)
        assert verify_password("samepassword", hash2)

    def test_hash_unicode_password(self):
        """Hash unicode password"""
        password = "密码пароль🔑"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed)

    def test_hash_empty_password(self):
        """Hash empty string password"""
        hashed = get_password_hash("")
        assert verify_password("", hashed)

    def test_hash_long_password(self):
        """Hash long password works via SHA-256 pre-hashing"""
        password = "A" * 100
        # With SHA-256 pre-hashing, long passwords should work fine
        hashed = get_password_hash(password)
        assert isinstance(hashed, str)
        assert verify_password(password, hashed)

    def test_hash_special_characters(self):
        """Hash password with special characters"""
        password = r"!@#$%^&*()_+-={}[]|\:\";<>?,./"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed)

    def test_hash_returns_string(self):
        """get_password_hash returns a string, not bytes"""
        hashed = get_password_hash("test")
        assert isinstance(hashed, str)
        # bcrypt hash starts with $2b$
        assert hashed.startswith("$2b$")
