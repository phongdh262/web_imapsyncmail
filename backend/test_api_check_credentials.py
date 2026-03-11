"""
Test Cases for Check Credentials API endpoints in main.py
Covers: /api/check-credentials, /api/check-credentials/bulk, /api/providers
Uses TestClient with mocked IMAP to avoid real connections.
"""

import pytest
import sys
import os
import io

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set ENV before importing app
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest"
os.environ["ADMIN_PASSWORD"] = "test-admin-password"
os.environ["DATABASE_URL"] = "sqlite:///./test_imapsync.db"
# Prevent load_dotenv() from loading MySQL credentials which causes hang
os.environ["DB_USER"] = ""
os.environ["DB_PASSWORD"] = ""
os.environ["DB_HOST"] = ""
os.environ["DB_NAME"] = ""

from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app, _rate_limit_store


@pytest.fixture(autouse=True)
def clear_rate_limit():
    """Clear rate limit store before each test."""
    _rate_limit_store.clear()
    yield
    _rate_limit_store.clear()


client = TestClient(app)


# =============================================
# 9.4 API Endpoints — CB-33 to CB-42
# =============================================

class TestCheckCredentialsAPI:
    """CB-33 → CB-42: Test API endpoints for credential checking."""

    @patch("main.check_imap_login")
    def test_cb33_single_check_valid(self, mock_login):
        """POST /api/check-credentials with valid data."""
        mock_login.return_value = {
            "email": "user@gmail.com",
            "status": "success",
            "message": "Login successful via imap.gmail.com",
            "provider": "Gmail"
        }
        resp = client.post("/api/check-credentials", json={
            "email": "user@gmail.com",
            "password": "app_password"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "user@gmail.com"
        assert data["status"] == "success"
        assert data["provider"] == "Gmail"

    @patch("main.check_imap_login")
    def test_cb34_single_check_custom_host(self, mock_login):
        """POST /api/check-credentials with custom host."""
        mock_login.return_value = {
            "email": "user@custom.vn",
            "status": "success",
            "message": "ok",
            "provider": "mail.vn"
        }
        resp = client.post("/api/check-credentials", json={
            "email": "user@custom.vn",
            "password": "pass",
            "host": "mail.vn",
            "port": 993
        })
        assert resp.status_code == 200
        mock_login.assert_called_once_with(
            email="user@custom.vn", password="pass", host="mail.vn", port=993
        )

    def test_cb35_single_check_missing_email(self):
        """POST /api/check-credentials without email → 422."""
        resp = client.post("/api/check-credentials", json={
            "password": "pass"
        })
        assert resp.status_code == 422

    def test_cb36_single_check_missing_password(self):
        """POST /api/check-credentials without password → 422."""
        resp = client.post("/api/check-credentials", json={
            "email": "user@gmail.com"
        })
        assert resp.status_code == 422

    @patch("main.check_bulk")
    def test_cb37_bulk_check_valid_csv(self, mock_bulk):
        """POST /api/check-credentials/bulk with valid CSV."""
        mock_bulk.return_value = [
            {"email": "a@gmail.com", "status": "success", "message": "ok", "provider": "Gmail"},
            {"email": "b@gmail.com", "status": "failed", "message": "auth fail", "provider": "Gmail"},
        ]
        csv_content = b"a@gmail.com,pass1\nb@gmail.com,pass2\n"
        resp = client.post(
            "/api/check-credentials/bulk?port=993",
            files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert data["success_count"] == 1
        assert data["failed_count"] == 1

    def test_cb38_bulk_check_empty_csv(self):
        """POST /api/check-credentials/bulk with empty CSV → 400."""
        csv_content = b"\n\n\n"
        resp = client.post(
            "/api/check-credentials/bulk?port=993",
            files={"file": ("empty.csv", io.BytesIO(csv_content), "text/csv")}
        )
        assert resp.status_code == 400
        assert "No valid credentials" in resp.json()["detail"]

    def test_cb39_bulk_check_single_column_csv(self):
        """POST /api/check-credentials/bulk with 1-column CSV → 400."""
        csv_content = b"email1@test.com\nemail2@test.com\n"
        resp = client.post(
            "/api/check-credentials/bulk?port=993",
            files={"file": ("bad.csv", io.BytesIO(csv_content), "text/csv")}
        )
        assert resp.status_code == 400

    @patch("main.check_bulk")
    def test_cb40_bulk_check_with_query_host(self, mock_bulk):
        """POST /api/check-credentials/bulk?host=mail.vn passes host to check_bulk."""
        mock_bulk.return_value = [
            {"email": "a@test.com", "status": "success", "message": "ok", "provider": "custom"},
        ]
        csv_content = b"a@test.com,pass1\n"
        resp = client.post(
            "/api/check-credentials/bulk?host=mail.vn&port=993",
            files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}
        )
        assert resp.status_code == 200
        mock_bulk.assert_called_once()
        call_kwargs = mock_bulk.call_args
        assert call_kwargs[1]["host"] == "mail.vn"

    def test_cb41_list_providers(self):
        """GET /api/providers returns provider list."""
        resp = client.get("/api/providers")
        assert resp.status_code == 200
        providers = resp.json()
        assert isinstance(providers, list)
        assert len(providers) > 0
        names = [p["name"] for p in providers]
        assert "Gmail" in names
        assert "Yandex" in names
        assert "Outlook" in names

    def test_cb42_providers_no_duplicates(self):
        """GET /api/providers returns unique provider names."""
        resp = client.get("/api/providers")
        providers = resp.json()
        names = [p["name"] for p in providers]
        assert len(names) == len(set(names)), "Duplicate provider names found!"


# =============================================
# Rate Limiting Tests
# =============================================

class TestRateLimiting:
    """Verify rate limiting on check-credentials endpoints."""

    @patch("main.check_imap_login")
    def test_rate_limit_exceeded(self, mock_login):
        """After 10 requests, should return 429."""
        mock_login.return_value = {
            "email": "x@gmail.com", "status": "success", "message": "ok", "provider": "Gmail"
        }
        # Send 10 requests (should be OK)
        for i in range(10):
            resp = client.post("/api/check-credentials", json={
                "email": f"user{i}@gmail.com", "password": "pass"
            })
            assert resp.status_code == 200, f"Request {i+1} should succeed"

        # 11th request should be rate-limited
        resp = client.post("/api/check-credentials", json={
            "email": "extra@gmail.com", "password": "pass"
        })
        assert resp.status_code == 429
        assert "Rate limit" in resp.json()["detail"]
