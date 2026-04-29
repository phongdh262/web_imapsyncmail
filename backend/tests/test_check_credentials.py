"""
Test Suite: Check Credentials — detect_provider, check_imap_login, check_bulk
Maps to: CB-01 → CB-32
"""
import pytest, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from unittest.mock import patch, MagicMock
from check_credentials import detect_provider, check_imap_login, check_bulk
import socket, imaplib

# =====================================================================
# detect_provider (CB-01 → CB-19)
# =====================================================================
class TestDetectProvider:
    @pytest.mark.parametrize("email,expected_host,expected_name", [
        ("user@gmail.com", "imap.gmail.com", "Gmail"),
        ("user@googlemail.com", "imap.gmail.com", "Gmail"),
        ("user@yandex.com", "imap.yandex.com", "Yandex"),
        ("user@yandex.ru", "imap.yandex.com", "Yandex"),
        ("user@ya.ru", "imap.yandex.com", "Yandex"),
        ("user@outlook.com", "outlook.office365.com", "Outlook"),
        ("user@hotmail.com", "outlook.office365.com", "Outlook"),
        ("user@live.com", "outlook.office365.com", "Outlook"),
        ("user@yahoo.com", "imap.mail.yahoo.com", "Yahoo"),
        ("user@yahoo.co.jp", "imap.mail.yahoo.co.jp", "Yahoo Japan"),
        ("user@zoho.com", "imap.zoho.com", "Zoho"),
        ("user@icloud.com", "imap.mail.me.com", "iCloud"),
        ("user@me.com", "imap.mail.me.com", "iCloud"),
        ("user@aol.com", "imap.aol.com", "AOL"),
        ("user@mail.ru", "imap.mail.ru", "Mail.ru"),
    ])
    def test_known_providers(self, email, expected_host, expected_name):
        result = detect_provider(email)
        assert result is not None
        assert result["host"] == expected_host
        assert result["name"] == expected_name

    def test_unknown_domain(self):
        assert detect_provider("user@unsupporteddomain.xyz") is None

    def test_no_at_sign(self):
        assert detect_provider("invalid-email") is None

    def test_whitespace_email(self):
        r = detect_provider("  test@yahoo.com  ")
        assert r["host"] == "imap.mail.yahoo.com"

    def test_uppercase_email(self):
        r = detect_provider("USER@GMAIL.COM")
        assert r["host"] == "imap.gmail.com"

    def test_empty_string(self):
        assert detect_provider("") is None

# =====================================================================
# check_imap_login (CB-20 → CB-27)
# =====================================================================
class TestCheckImapLogin:
    @patch('check_credentials.imaplib.IMAP4_SSL')
    def test_success(self, mock_imap):
        mock_inst = MagicMock(); mock_imap.return_value = mock_inst
        r = check_imap_login("user@gmail.com", "password123")
        assert r["status"] == "success"
        assert r["provider"] == "Gmail"
        assert "successful" in r["message"].lower()
        mock_inst.login.assert_called_with("user@gmail.com", "password123")
        mock_inst.logout.assert_called_once()

    @patch('check_credentials.imaplib.IMAP4_SSL')
    def test_auth_fail(self, mock_imap):
        mock_inst = MagicMock()
        mock_inst.login.side_effect = imaplib.IMAP4.error("AUTHENTICATIONFAILED")
        mock_imap.return_value = mock_inst
        r = check_imap_login("user@yandex.com", "wrongpass")
        assert r["status"] == "failed"
        assert "Authentication failed" in r["message"]

    @patch('check_credentials.imaplib.IMAP4_SSL')
    def test_timeout(self, mock_imap):
        mock_imap.side_effect = socket.timeout("timeout")
        r = check_imap_login("user@outlook.com", "pass")
        assert r["status"] == "failed"
        assert "timed out" in r["message"].lower()

    @patch('check_credentials.imaplib.IMAP4_SSL')
    def test_network_error(self, mock_imap):
        mock_imap.side_effect = socket.gaierror("DNS failed")
        r = check_imap_login("user@gmail.com", "pass")
        assert r["status"] == "failed"
        assert "Cannot connect" in r["message"]

    @patch.dict('sys.modules', {'dns': MagicMock(), 'dns.resolver': MagicMock(resolve=MagicMock(side_effect=Exception("no DNS")))})
    def test_unknown_domain_no_host(self):
        # Re-import to pick up mocked dns
        import importlib
        import check_credentials as cc
        importlib.reload(cc)
        r = cc.check_imap_login("user@unknown.xyz", "pass")
        assert r["status"] == "failed"
        assert "Cannot detect IMAP server" in r["message"]
        assert r["provider"] == "Unknown"

    @patch('check_credentials.imaplib.IMAP4_SSL')
    def test_custom_host(self, mock_imap):
        mock_inst = MagicMock(); mock_imap.return_value = mock_inst
        r = check_imap_login("user@custom.vn", "pass", host="mail.custom.vn", port=993)
        assert r["status"] == "success"
        mock_imap.assert_called_once()

    @patch('check_credentials.imaplib.IMAP4_SSL')
    def test_strips_whitespace(self, mock_imap):
        mock_inst = MagicMock(); mock_imap.return_value = mock_inst
        r = check_imap_login("  user@gmail.com  ", "  pass  ")
        assert r["status"] == "success"
        mock_inst.login.assert_called_with("user@gmail.com", "pass")

    @patch('check_credentials.imaplib.IMAP4_SSL')
    def test_server_alert(self, mock_imap):
        mock_inst = MagicMock()
        mock_inst.login.side_effect = imaplib.IMAP4.error("ALERT: Account locked")
        mock_imap.return_value = mock_inst
        r = check_imap_login("user@gmail.com", "pass")
        assert r["status"] == "failed"

    @patch('check_credentials.imaplib.IMAP4_SSL')
    def test_unexpected_exception(self, mock_imap):
        mock_imap.side_effect = RuntimeError("unexpected")
        r = check_imap_login("user@gmail.com", "pass")
        assert r["status"] == "failed"
        assert "Unexpected error" in r["message"]

# =====================================================================
# check_bulk (CB-28 → CB-32)
# =====================================================================
class TestCheckBulk:
    @patch('check_credentials.check_imap_login')
    def test_bulk_basic(self, mock_check):
        def se(email, password, host, port):
            return {"email": email, "status": "success" if "good" in email else "failed", "message": "ok"}
        mock_check.side_effect = se
        creds = [{"email": "good@gmail.com", "password": "p"}, {"email": "fail@y.com", "password": "p"}]
        results = check_bulk(creds)
        assert len(results) == 2
        assert results[0]["email"] == "good@gmail.com"
        assert results[0]["status"] == "success"
        assert results[1]["status"] == "failed"

    @patch('check_credentials.check_imap_login')
    def test_bulk_preserves_order(self, mock_check):
        mock_check.side_effect = lambda e, p, h, port: {"email": e, "status": "success", "message": "ok"}
        creds = [{"email": f"u{i}@g.com", "password": "p"} for i in range(5)]
        results = check_bulk(creds)
        for i, r in enumerate(results):
            assert r["email"] == f"u{i}@g.com"

    @patch('check_credentials.check_imap_login')
    def test_bulk_handles_exception(self, mock_check):
        def se(email, password, host, port):
            if "bad" in email: raise RuntimeError("boom")
            return {"email": email, "status": "success", "message": "ok"}
        mock_check.side_effect = se
        creds = [{"email": "good@g.com", "password": "p"}, {"email": "bad@g.com", "password": "p"}]
        results = check_bulk(creds)
        assert len(results) == 2
        bad = [r for r in results if "bad" in r["email"]][0]
        assert bad["status"] == "failed"
        assert "Check error" in bad["message"]

    @patch('check_credentials.check_imap_login')
    def test_bulk_custom_host(self, mock_check):
        mock_check.side_effect = lambda e, p, h, port: {"email": e, "status": "success", "message": f"via {h}"}
        creds = [{"email": "u@x.com", "password": "p"}]
        results = check_bulk(creds, host="mail.custom.vn", port=993)
        assert "mail.custom.vn" in results[0]["message"]
