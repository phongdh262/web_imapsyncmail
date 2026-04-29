"""
Test Suite: API — Check Credentials Endpoints + Rate Limit
Maps to: CB-33 → CB-42, RL-01
"""
import pytest, os, sys, io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from unittest.mock import patch


class TestSingleCheckAPI:
    @patch("main.check_imap_login")
    def test_single_check_success(self, mock_check, admin_client):
        """CB-33: POST single check returns result."""
        mock_check.return_value = {"email": "u@g.com", "status": "success", "message": "OK", "provider": "Gmail"}
        c, csrf = admin_client
        r = c.post("/api/check-credentials", json={"email": "u@g.com", "password": "p"},
                    headers={"X-CSRF-Token": csrf})
        assert r.status_code == 200
        b = r.json()
        assert b["status"] == "success"
        assert b["provider"] == "Gmail"

    @patch("main.check_imap_login")
    def test_single_check_with_custom_host(self, mock_check, admin_client):
        """CB-34: Custom host/port passed to backend."""
        mock_check.return_value = {"email": "u@x.vn", "status": "success", "message": "via mail.vn", "provider": "mail.vn"}
        c, csrf = admin_client
        r = c.post("/api/check-credentials", json={"email": "u@x.vn", "password": "p", "host": "mail.vn", "port": 993},
                    headers={"X-CSRF-Token": csrf})
        assert r.status_code == 200
        mock_check.assert_called_once_with(email="u@x.vn", password="p", host="mail.vn", port=993)

    def test_single_check_missing_email(self, admin_client):
        """CB-35: Missing email returns 422."""
        c, csrf = admin_client
        r = c.post("/api/check-credentials", json={"password": "p"}, headers={"X-CSRF-Token": csrf})
        assert r.status_code == 422

    def test_single_check_missing_password(self, admin_client):
        """CB-36: Missing password returns 422."""
        c, csrf = admin_client
        r = c.post("/api/check-credentials", json={"email": "u@g.com"}, headers={"X-CSRF-Token": csrf})
        assert r.status_code == 422


class TestBulkCheckAPI:
    @patch("main.check_bulk")
    def test_bulk_check_csv_valid(self, mock_bulk, admin_client):
        """CB-37: Bulk CSV upload returns results."""
        mock_bulk.return_value = [
            {"email": "a@g.com", "status": "success", "message": "OK", "provider": "Gmail"},
            {"email": "b@g.com", "status": "failed", "message": "Fail", "provider": "Gmail"},
        ]
        c, csrf = admin_client
        csv = "a@g.com,pass1\nb@g.com,pass2\n"
        r = c.post("/api/check-credentials/bulk",
                    data={"port": "993"},
                    files={"file": ("test.csv", io.BytesIO(csv.encode()), "text/csv")},
                    headers={"X-CSRF-Token": csrf})
        assert r.status_code == 200
        b = r.json()
        assert b["total"] == 2
        assert b["success_count"] == 1
        assert b["failed_count"] == 1

    def test_bulk_check_csv_empty(self, admin_client):
        """CB-38: Empty CSV returns 400."""
        c, csrf = admin_client
        csv = "\n\n"
        r = c.post("/api/check-credentials/bulk",
                    data={"port": "993"},
                    files={"file": ("test.csv", io.BytesIO(csv.encode()), "text/csv")},
                    headers={"X-CSRF-Token": csrf})
        assert r.status_code == 400

    def test_bulk_check_csv_one_column(self, admin_client):
        """CB-39: CSV with only email column returns 400."""
        c, csrf = admin_client
        csv = "email_only@g.com\nanother@g.com\n"
        r = c.post("/api/check-credentials/bulk",
                    data={"port": "993"},
                    files={"file": ("test.csv", io.BytesIO(csv.encode()), "text/csv")},
                    headers={"X-CSRF-Token": csrf})
        assert r.status_code == 400


class TestProviderAPI:
    def test_list_providers(self, admin_client):
        """CB-41: GET /api/providers returns provider list."""
        c, _ = admin_client
        r = c.get("/api/providers")
        assert r.status_code == 200
        providers = r.json()
        assert isinstance(providers, list)
        names = [p["name"] for p in providers]
        assert "Gmail" in names
        assert "Yandex" in names

    def test_providers_no_duplicates(self, admin_client):
        """CB-42: Each provider name appears exactly once."""
        c, _ = admin_client
        r = c.get("/api/providers")
        names = [p["name"] for p in r.json()]
        assert len(names) == len(set(names))


class TestRateLimit:
    @patch("main.check_imap_login")
    def test_rate_limit_exceeded(self, mock_check, admin_client):
        """RL-01: Exceeding rate limit returns 429."""
        mock_check.return_value = {"email": "u@g.com", "status": "success", "message": "OK", "provider": "G"}
        c, csrf = admin_client
        # Single check rate limit is 20/300s
        for i in range(21):
            r = c.post("/api/check-credentials", json={"email": f"u{i}@g.com", "password": "p"},
                        headers={"X-CSRF-Token": csrf})
            if r.status_code == 429:
                break
        assert r.status_code == 429
        assert "Rate limit" in r.json()["detail"]
