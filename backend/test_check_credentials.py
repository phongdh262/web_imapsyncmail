"""
Test Cases for check_credentials.py
Covers: detect_provider(), check_imap_login(), check_bulk()
Uses unittest.mock to avoid real IMAP connections.
"""

import pytest
import sys
import os
import imaplib
import socket
from unittest.mock import patch, MagicMock

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_credentials import detect_provider, check_imap_login, check_bulk, PROVIDER_MAP


# =============================================
# 9.1 detect_provider() — CB-01 to CB-19
# =============================================

class TestDetectProvider:
    """CB-01 → CB-19: Test provider auto-detection from email domain."""

    def test_cb01_gmail(self):
        result = detect_provider("user@gmail.com")
        assert result["host"] == "imap.gmail.com"
        assert result["port"] == 993
        assert result["name"] == "Gmail"

    def test_cb02_googlemail(self):
        result = detect_provider("user@googlemail.com")
        assert result["host"] == "imap.gmail.com"
        assert result["name"] == "Gmail"

    def test_cb03_yandex_com(self):
        result = detect_provider("user@yandex.com")
        assert result["host"] == "imap.yandex.com"
        assert result["name"] == "Yandex"

    def test_cb04_yandex_ru(self):
        result = detect_provider("user@yandex.ru")
        assert result["host"] == "imap.yandex.com"
        assert result["name"] == "Yandex"

    def test_cb05_ya_ru(self):
        result = detect_provider("user@ya.ru")
        assert result["host"] == "imap.yandex.com"
        assert result["name"] == "Yandex"

    def test_cb06_outlook(self):
        result = detect_provider("user@outlook.com")
        assert result["host"] == "outlook.office365.com"
        assert result["name"] == "Outlook"

    def test_cb07_hotmail(self):
        result = detect_provider("user@hotmail.com")
        assert result["host"] == "outlook.office365.com"
        assert result["name"] == "Outlook"

    def test_cb08_live(self):
        result = detect_provider("user@live.com")
        assert result["host"] == "outlook.office365.com"
        assert result["name"] == "Outlook"

    def test_cb09_yahoo(self):
        result = detect_provider("user@yahoo.com")
        assert result["host"] == "imap.mail.yahoo.com"
        assert result["name"] == "Yahoo"

    def test_cb10_yahoo_japan(self):
        result = detect_provider("user@yahoo.co.jp")
        assert result["host"] == "imap.mail.yahoo.co.jp"
        assert result["name"] == "Yahoo Japan"

    def test_cb11_zoho(self):
        result = detect_provider("user@zoho.com")
        assert result["host"] == "imap.zoho.com"
        assert result["name"] == "Zoho"

    def test_cb12_icloud(self):
        result = detect_provider("user@icloud.com")
        assert result["host"] == "imap.mail.me.com"
        assert result["name"] == "iCloud"

    def test_cb13_me_com(self):
        result = detect_provider("user@me.com")
        assert result["host"] == "imap.mail.me.com"
        assert result["name"] == "iCloud"

    def test_cb14_aol(self):
        result = detect_provider("user@aol.com")
        assert result["host"] == "imap.aol.com"
        assert result["name"] == "AOL"

    def test_cb15_mail_ru(self):
        result = detect_provider("user@mail.ru")
        assert result["host"] == "imap.mail.ru"
        assert result["name"] == "Mail.ru"

    def test_cb16_unsupported_domain(self):
        result = detect_provider("user@custom.vn")
        assert result is None

    def test_cb17_no_at_sign(self):
        result = detect_provider("invalid-email")
        assert result is None

    def test_cb18_whitespace(self):
        result = detect_provider("  user@gmail.com  ")
        assert result is not None
        assert result["name"] == "Gmail"

    def test_cb19_uppercase(self):
        result = detect_provider("User@GMAIL.COM")
        assert result is not None
        assert result["name"] == "Gmail"


# =============================================
# 9.2 check_imap_login() — CB-20 to CB-27
# =============================================

class TestCheckImapLogin:
    """CB-20 → CB-27: Test IMAP login with mocked connections."""

    @patch("check_credentials.imaplib.IMAP4_SSL")
    def test_cb20_login_success_auto_detect(self, mock_imap_cls):
        """Successful login with auto-detected Gmail provider."""
        mock_imap = MagicMock()
        mock_imap_cls.return_value = mock_imap
        mock_imap.login.return_value = ("OK", [b"Logged in"])

        result = check_imap_login("user@gmail.com", "correct_pass")

        assert result["status"] == "success"
        assert "imap.gmail.com" in result["message"]
        assert result["provider"] == "Gmail"
        mock_imap.login.assert_called_once_with("user@gmail.com", "correct_pass")
        mock_imap.logout.assert_called_once()

    @patch("check_credentials.imaplib.IMAP4_SSL")
    def test_cb21_login_wrong_password(self, mock_imap_cls):
        """Failed login with wrong password."""
        mock_imap = MagicMock()
        mock_imap_cls.return_value = mock_imap
        mock_imap.login.side_effect = imaplib.IMAP4.error("AUTHENTICATIONFAILED")

        result = check_imap_login("user@gmail.com", "wrong_pass")

        assert result["status"] == "failed"
        assert "Authentication failed" in result["message"]

    @patch("check_credentials.imaplib.IMAP4_SSL")
    def test_cb22_custom_host(self, mock_imap_cls):
        """Login with custom host specified."""
        mock_imap = MagicMock()
        mock_imap_cls.return_value = mock_imap
        mock_imap.login.return_value = ("OK", [b"ok"])

        result = check_imap_login("user@custom.vn", "pass", host="mail.custom.vn", port=993)

        assert result["status"] == "success"
        assert result["provider"] == "mail.custom.vn"
        mock_imap_cls.assert_called_once()

    def test_cb23_unsupported_no_host(self):
        """Unsupported domain without host should return failed immediately."""
        result = check_imap_login("user@unknown.xyz", "pass")

        assert result["status"] == "failed"
        assert "Cannot detect IMAP server" in result["message"]
        assert result["provider"] == "Unknown"

    @patch("check_credentials.imaplib.IMAP4_SSL")
    def test_cb24_connection_timeout(self, mock_imap_cls):
        """Connection timeout returns proper error."""
        mock_imap_cls.side_effect = socket.timeout()

        result = check_imap_login("user@gmail.com", "pass")

        assert result["status"] == "failed"
        assert "Connection timed out" in result["message"]

    @patch("check_credentials.imaplib.IMAP4_SSL")
    def test_cb25_dns_error(self, mock_imap_cls):
        """DNS/network error returns proper error."""
        mock_imap_cls.side_effect = socket.gaierror("Name resolution failed")

        result = check_imap_login("user@gmail.com", "pass")

        assert result["status"] == "failed"
        assert "Cannot connect to" in result["message"]

    @patch("check_credentials.imaplib.IMAP4_SSL")
    def test_cb26_imap_alert(self, mock_imap_cls):
        """IMAP server alert."""
        mock_imap = MagicMock()
        mock_imap_cls.return_value = mock_imap
        mock_imap.login.side_effect = imaplib.IMAP4.error("ALERT: Please log in via web browser")

        result = check_imap_login("user@gmail.com", "pass")

        assert result["status"] == "failed"
        assert "Server alert" in result["message"]

    @patch("check_credentials.imaplib.IMAP4_SSL")
    def test_cb27_whitespace_strip(self, mock_imap_cls):
        """Email and password with whitespace get stripped."""
        mock_imap = MagicMock()
        mock_imap_cls.return_value = mock_imap
        mock_imap.login.return_value = ("OK", [b"ok"])

        result = check_imap_login("  user@gmail.com  ", "  password  ")

        mock_imap.login.assert_called_once_with("user@gmail.com", "password")
        assert result["status"] == "success"


# =============================================
# 9.3 check_bulk() — CB-28 to CB-32
# =============================================

class TestCheckBulk:
    """CB-28 → CB-32: Test bulk credential checking."""

    @patch("check_credentials.check_imap_login")
    def test_cb28_bulk_multiple(self, mock_login):
        """Bulk check returns result for each credential."""
        mock_login.side_effect = [
            {"email": "a@gmail.com", "status": "success", "message": "ok", "provider": "Gmail"},
            {"email": "b@yandex.ru", "status": "failed", "message": "auth fail", "provider": "Yandex"},
            {"email": "c@yahoo.com", "status": "success", "message": "ok", "provider": "Yahoo"},
        ]
        creds = [
            {"email": "a@gmail.com", "password": "p1"},
            {"email": "b@yandex.ru", "password": "p2"},
            {"email": "c@yahoo.com", "password": "p3"},
        ]
        results = check_bulk(creds)

        assert len(results) == 3
        assert mock_login.call_count == 3

    @patch("check_credentials.check_imap_login")
    def test_cb29_bulk_preserves_order(self, mock_login):
        """Results sorted by original order."""
        mock_login.side_effect = [
            {"email": "c@gmail.com", "status": "success", "message": "ok", "provider": "Gmail"},
            {"email": "a@gmail.com", "status": "success", "message": "ok", "provider": "Gmail"},
            {"email": "b@gmail.com", "status": "success", "message": "ok", "provider": "Gmail"},
        ]
        creds = [
            {"email": "a@gmail.com", "password": "p1"},
            {"email": "b@gmail.com", "password": "p2"},
            {"email": "c@gmail.com", "password": "p3"},
        ]
        results = check_bulk(creds)

        assert results[0]["email"] == "a@gmail.com"
        assert results[1]["email"] == "b@gmail.com"
        assert results[2]["email"] == "c@gmail.com"

    @patch("check_credentials.check_imap_login")
    def test_cb31_bulk_exception_handling(self, mock_login):
        """Exception in one thread doesn't crash bulk check."""
        mock_login.side_effect = [
            {"email": "a@gmail.com", "status": "success", "message": "ok", "provider": "Gmail"},
            Exception("Connection reset"),
        ]
        creds = [
            {"email": "a@gmail.com", "password": "p1"},
            {"email": "b@gmail.com", "password": "p2"},
        ]
        results = check_bulk(creds)

        assert len(results) == 2
        failed = [r for r in results if r["status"] == "failed"]
        assert len(failed) == 1
        assert "Check error" in failed[0]["message"]

    @patch("check_credentials.check_imap_login")
    def test_cb32_bulk_custom_host(self, mock_login):
        """Custom host passed to all credentials."""
        mock_login.return_value = {"email": "a@test.com", "status": "success", "message": "ok", "provider": "custom"}
        creds = [{"email": "a@test.com", "password": "p1"}]

        check_bulk(creds, host="mail.custom.vn", port=993)

        mock_login.assert_called_once_with("a@test.com", "p1", "mail.custom.vn", 993)
