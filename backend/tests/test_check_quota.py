"""
Test Suite: Check Quota sync-estimate coverage and dedupe.
"""
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from check_quota import _select_sync_folders, check_mailbox_quota


class TestFolderSelection:
    def test_skip_trash_matches_sync_default(self):
        folders = [
            {"name": "INBOX", "attributes": ["\\hasnochildren"], "selectable": True},
            {"name": "Trash", "attributes": ["\\trash"], "selectable": True},
            {"name": "Deleted Items", "attributes": [], "selectable": True},
            {"name": "Root", "attributes": ["\\noselect"], "selectable": False},
        ]

        selection = _select_sync_folders(folders, skip_trash=True)

        assert selection["strategy"] == "sync_rules_skip_trash"
        assert [folder["name"] for folder in selection["folders"]] == ["INBOX"]
        assert set(selection["skipped_folders"]) == {"Trash", "Deleted Items", "Root"}

    def test_can_include_trash_when_requested(self):
        folders = [
            {"name": "INBOX", "attributes": ["\\hasnochildren"], "selectable": True},
            {"name": "Trash", "attributes": ["\\trash"], "selectable": True},
        ]

        selection = _select_sync_folders(folders, skip_trash=False)

        assert selection["strategy"] == "sync_rules_include_trash"
        assert [folder["name"] for folder in selection["folders"]] == ["INBOX", "Trash"]


class FakeSyncEstimateImap:
    def __init__(self, host, port, ssl_context=None, timeout=None):
        self.selected_folder = None
        self.folder_messages = {
            "INBOX": [
                {"uid": "11", "size": 100, "message_id": "<same-1@example.com>"},
                {"uid": "12", "size": 200, "message_id": "<unique-inbox@example.com>"},
            ],
            "Sent": [
                {"uid": "21", "size": 100, "message_id": "<same-1@example.com>"},
                {"uid": "22", "size": 300, "message_id": "<unique-sent@example.com>"},
            ],
            "Trash": [
                {"uid": "31", "size": 50, "message_id": "<trash-only@example.com>"},
            ],
            "Archive": [
                {"uid": "41", "size": 125, "message_id": None},
            ],
        }

    def login(self, email, password):
        return "OK", [b"logged in"]

    def getquotaroot(self, mailbox):
        return "OK", [[b"INBOX"], [b"(STORAGE 0 7516192768)"]]

    def list(self):
        return "OK", [
            b'(\\HasNoChildren) "/" "INBOX"',
            b'(\\HasNoChildren \\Sent) "/" "Sent"',
            b'(\\HasNoChildren \\Trash) "/" "Trash"',
            b'(\\HasNoChildren) "/" "Archive"',
        ]

    def select(self, mailbox, readonly=True):
        folder_name = mailbox.strip('"')
        self.selected_folder = folder_name
        messages = self.folder_messages.get(folder_name, [])
        return "OK", [str(len(messages)).encode()]

    def fetch(self, fetch_range, query):
        messages = self.folder_messages.get(self.selected_folder, [])
        start, end = [int(part) for part in fetch_range.split(":")]
        items = []
        for idx in range(start - 1, min(end, len(messages))):
            message = messages[idx]
            header = (
                f"Message-ID: {message['message_id']}\r\n\r\n".encode()
                if message["message_id"]
                else b"\r\n"
            )
            items.append((
                f"{idx + 1} (UID {message['uid']} RFC822.SIZE {message['size']} BODY[HEADER.FIELDS (MESSAGE-ID)] {{{len(header)}}}".encode(),
                header,
            ))
            items.append(b")")
        return "OK", items

    def logout(self):
        return "BYE", [b"logout"]


class TestCheckMailboxQuotaSyncEstimate:
    @patch("check_quota.imaplib.IMAP4_SSL", FakeSyncEstimateImap)
    def test_sync_estimate_dedupes_by_message_id_and_skips_trash_by_default(self):
        result = check_mailbox_quota("user@example.com", "secret", host="mail.example.com", skip_trash=True)

        assert result["status"] == "success"
        assert result["scan_strategy"] == "sync_rules_skip_trash"
        assert result["method"] == "QUOTA+SYNC_ESTIMATE"
        assert result["scanned_folders"] == ["INBOX", "Sent", "Archive"]
        assert "Trash" in result["skipped_folders"]

        # Unique synced messages: same-1, unique-inbox, unique-sent, archive-without-id
        assert result["total_messages"] == 4
        assert result["quota_used"] == 725

        # Raw scanned data still includes the duplicate in Sent.
        assert result["raw_total_messages"] == 5
        assert result["raw_total_size"] == 825
        assert result["duplicate_messages"] == 1
        assert result["duplicate_bytes"] == 100
        assert result["missing_message_id_count"] == 1
        assert "skipped 1 duplicate messages" in result["message"]
        assert "skip_trash" not in result["message"]

    @patch("check_quota.imaplib.IMAP4_SSL", FakeSyncEstimateImap)
    def test_sync_estimate_can_include_trash(self):
        result = check_mailbox_quota("user@example.com", "secret", host="mail.example.com", skip_trash=False)

        assert result["status"] == "success"
        assert result["scan_strategy"] == "sync_rules_include_trash"
        assert "Trash" in result["scanned_folders"]
        assert result["total_messages"] == 5
        assert result["quota_used"] == 775
