"""
Test Suite: Check Quota coverage and folder selection.
"""
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from check_quota import _prioritize_folders, check_mailbox_quota


class TestFolderSelection:
    def test_gmail_prefers_all_mail_plus_spam_and_trash(self):
        folders = [
            {"name": "[Gmail]", "attributes": ["\\noselect"], "selectable": False},
            {"name": "[Gmail]/All Mail", "attributes": ["\\all"], "selectable": True},
            {"name": "[Gmail]/Spam", "attributes": ["\\junk"], "selectable": True},
            {"name": "[Gmail]/Trash", "attributes": ["\\trash"], "selectable": True},
            {"name": "[Gmail]/Sent Mail", "attributes": ["\\sent"], "selectable": True},
        ]

        selection = _prioritize_folders(folders)

        assert selection["strategy"] == "all_mail_plus_spam_trash"
        assert [folder["name"] for folder in selection["folders"]] == [
            "[Gmail]/All Mail",
            "[Gmail]/Spam",
            "[Gmail]/Trash",
        ]
        assert "[Gmail]/Sent Mail" in selection["skipped_folders"]
        assert "[Gmail]" in selection["skipped_folders"]

    def test_non_gmail_scans_all_selectable_folders(self):
        folders = [
            {"name": "INBOX", "attributes": ["\\hasnochildren"], "selectable": True},
            {"name": "Archive", "attributes": ["\\hasnochildren"], "selectable": True},
            {"name": "Root", "attributes": ["\\noselect"], "selectable": False},
        ]

        selection = _prioritize_folders(folders)

        assert selection["strategy"] == "all_selectable_folders"
        assert [folder["name"] for folder in selection["folders"]] == ["INBOX", "Archive"]
        assert selection["skipped_folders"] == ["Root"]


class FakeGmailImap:
    def __init__(self, host, port, ssl_context=None, timeout=None):
        self.selected_folder = None
        self.folder_messages = {
            '"[Gmail]/All Mail"': [100, 200],
            '"[Gmail]/Spam"': [50],
            '"[Gmail]/Trash"': [70],
            '"[Gmail]/Sent Mail"': [500],
        }

    def login(self, email, password):
        return "OK", [b"logged in"]

    def getquotaroot(self, mailbox):
        return "OK", [[b"INBOX"], [b"(STORAGE 0 7516192768)"]]

    def list(self):
        return "OK", [
            b'(\\Noselect \\HasChildren) "/" "[Gmail]"',
            b'(\\HasNoChildren \\All) "/" "[Gmail]/All Mail"',
            b'(\\HasNoChildren \\Junk) "/" "[Gmail]/Spam"',
            b'(\\HasNoChildren \\Trash) "/" "[Gmail]/Trash"',
            b'(\\HasNoChildren \\Sent) "/" "[Gmail]/Sent Mail"',
        ]

    def select(self, mailbox, readonly=True):
        self.selected_folder = mailbox
        messages = self.folder_messages.get(mailbox, [])
        return "OK", [str(len(messages)).encode()]

    def fetch(self, fetch_range, query):
        messages = self.folder_messages.get(self.selected_folder, [])
        start, end = [int(part) for part in fetch_range.split(":")]
        items = []
        for idx in range(start - 1, min(end, len(messages))):
            items.append(f"{idx + 1} (RFC822.SIZE {messages[idx]})".encode())
        return "OK", items

    def logout(self):
        return "BYE", [b"logout"]


class TestCheckMailboxQuotaCoverage:
    @patch("check_quota.imaplib.IMAP4_SSL", FakeGmailImap)
    def test_gmail_scan_includes_spam_and_trash_but_not_sent_duplicates(self):
        result = check_mailbox_quota("user@example.com", "secret", host="mail.example.com")

        assert result["status"] == "success"
        assert result["scan_strategy"] == "all_mail_plus_spam_trash"
        assert result["scanned_folders"] == [
            "[Gmail]/All Mail",
            "[Gmail]/Spam",
            "[Gmail]/Trash",
        ]
        assert "[Gmail]/Sent Mail" in result["skipped_folders"]
        assert result["total_messages"] == 4
        assert result["quota_used"] == 420
        assert result["scan_complete"] is True
        assert "All Mail + Spam + Trash" in result["message"]
