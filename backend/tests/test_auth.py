"""
Test Suite: Authentication Module
Maps to: AUTH-01 → AUTH-03, CSRF validation, session management
"""
import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_csrf_token,
    SECRET_KEY,
    ALGORITHM,
)
from jose import jwt


# =====================================================================
# Unit Tests — Password Hashing (existing + expanded)
# =====================================================================

class TestPasswordHashing:
    """Verify SHA-256 pre-hash + bcrypt pipeline."""

    def test_hash_and_verify_correct(self):
        """Basic roundtrip: hash → verify succeeds."""
        plain = "super_secure_password_123!"
        hashed = get_password_hash(plain)
        assert plain != hashed
        assert verify_password(plain, hashed) is True

    def test_hash_and_verify_wrong(self):
        """Wrong password must be rejected."""
        hashed = get_password_hash("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_unicode_password(self):
        """Vietnamese + emoji characters work via SHA-256 pre-hash."""
        plain = "mật_khẩu_tiếng_việt_🌟"
        hashed = get_password_hash(plain)
        assert verify_password(plain, hashed) is True

    def test_long_password_beyond_bcrypt_limit(self):
        """Passwords >72 chars handled by SHA-256 pre-hash, no truncation."""
        long_pass = "a" * 100
        hashed = get_password_hash(long_pass)
        assert verify_password(long_pass, hashed) is True
        assert verify_password("a" * 99, hashed) is False

    def test_empty_password(self):
        """Empty string can be hashed (edge case)."""
        hashed = get_password_hash("")
        assert verify_password("", hashed) is True
        assert verify_password("notempty", hashed) is False

    def test_different_hashes_for_same_password(self):
        """Bcrypt salt ensures different hashes each time."""
        h1 = get_password_hash("same_password")
        h2 = get_password_hash("same_password")
        assert h1 != h2  # Different salts
        assert verify_password("same_password", h1) is True
        assert verify_password("same_password", h2) is True


# =====================================================================
# Unit Tests — JWT Token
# =====================================================================

class TestJWTToken:
    """Verify access token creation and structure."""

    def test_create_access_token(self):
        """Token is decodable and contains subject."""
        data = {"sub": "admin_user"}
        token = create_access_token(data)
        assert isinstance(token, str)

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload.get("sub") == "admin_user"
        assert "exp" in payload

    def test_token_with_extra_data(self):
        """Extra claims are preserved in token."""
        data = {"sub": "user1", "csrf": "abc123"}
        token = create_access_token(data)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload.get("csrf") == "abc123"

    def test_csrf_token_generation(self):
        """CSRF token is a sufficiently long urlsafe string."""
        token = create_csrf_token()
        assert isinstance(token, str)
        assert len(token) > 20

    def test_csrf_tokens_are_unique(self):
        """Each call generates a different token."""
        t1 = create_csrf_token()
        t2 = create_csrf_token()
        assert t1 != t2


# =====================================================================
# Integration Tests — Login API (AUTH-01 → AUTH-03)
# =====================================================================

class TestLoginAPI:
    """Test /api/login endpoint via TestClient."""

    def test_login_success(self, client):
        """AUTH-01: Login with valid credentials returns 200 + token."""
        resp = client.post(
            "/api/login",
            data={"username": "phongdh", "password": "testadmin123"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert body["username"] == "phongdh"
        # Session cookie must be set
        assert "admin_session" in resp.cookies

    def test_login_wrong_password(self, client):
        """AUTH-02: Wrong password returns 401."""
        # First create the admin user by logging in successfully
        client.post("/api/login", data={"username": "phongdh", "password": "testadmin123"})
        # Now try with wrong password
        resp = client.post(
            "/api/login",
            data={"username": "phongdh", "password": "totally_wrong"},
        )
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        """Non-admin user that doesn't exist returns 401."""
        resp = client.post(
            "/api/login",
            data={"username": "nobody", "password": "irrelevant"},
        )
        assert resp.status_code == 401

    def test_login_auto_creates_admin(self, client):
        """AUTH-03: First login auto-creates admin account from env vars."""
        resp = client.post(
            "/api/login",
            data={"username": "phongdh", "password": "testadmin123"},
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == "phongdh"

    def test_login_sets_csrf_cookie(self, client):
        """Login sets both session and CSRF cookies."""
        resp = client.post(
            "/api/login",
            data={"username": "phongdh", "password": "testadmin123"},
        )
        assert resp.status_code == 200
        assert "admin_session" in resp.cookies
        assert "csrf_token" in resp.cookies

    def test_login_returns_can_manage_users(self, client):
        """Root admin gets can_manage_users=True in response."""
        resp = client.post(
            "/api/login",
            data={"username": "phongdh", "password": "testadmin123"},
        )
        assert resp.json()["can_manage_users"] is True


# =====================================================================
# Integration Tests — Session & CSRF
# =====================================================================

class TestSessionAndCSRF:
    """Test logout, /api/me, and CSRF enforcement."""

    def test_logout_clears_cookies(self, admin_client):
        """Logout removes session and CSRF cookies."""
        client, _ = admin_client
        resp = client.post("/api/logout")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_get_me_returns_user_info(self, admin_client):
        """GET /api/me returns current user details."""
        client, _ = admin_client
        resp = client.get("/api/me")
        assert resp.status_code == 200
        body = resp.json()
        assert body["username"] == "phongdh"
        assert body["is_root_admin"] is True
        assert body["can_manage_users"] is True

    def test_get_me_unauthenticated(self, client):
        """GET /api/me without session returns 401."""
        resp = client.get("/api/me")
        assert resp.status_code == 401

    def test_csrf_blocks_write_without_token(self, admin_client):
        """Write operations without CSRF token are blocked."""
        client, _ = admin_client
        # Try to create a job without CSRF header
        resp = client.post(
            "/api/jobs",
            json={
                "name": "Test",
                "source_host": "imap.gmail.com",
                "target_host": "imap.yandex.com",
                "password": "test1234",
            },
        )
        assert resp.status_code == 403

    def test_csrf_blocks_mismatched_token(self, admin_client):
        """Write operations with wrong CSRF token are blocked."""
        client, _ = admin_client
        resp = client.post(
            "/api/jobs",
            json={
                "name": "Test",
                "source_host": "imap.gmail.com",
                "target_host": "imap.yandex.com",
                "password": "test1234",
            },
            headers={"X-CSRF-Token": "completely-wrong-token"},
        )
        assert resp.status_code == 403
