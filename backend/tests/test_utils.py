"""
Test Suite: Utility Functions
Tests: format_job_response, _sync_job_runtime, normalize helpers, is_root_admin
"""
import pytest, os, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from unittest.mock import MagicMock
from fastapi import HTTPException


# =====================================================================
# format_job_response — Data Formatting
# =====================================================================
class TestFormatJobResponse:
    def _make_job(self, **kw):
        from database import Job
        defaults = dict(id="j1", name="Test", status="completed", total_mailboxes=10,
                        completed=8, failed=2, source_host="a.com", target_host="b.com",
                        data_transferred=0)
        defaults.update(kw)
        j = MagicMock(spec=Job)
        for k, v in defaults.items():
            setattr(j, k, v)
        j.created_at = MagicMock()
        j.created_at.isoformat.return_value = "2026-01-01T00:00:00"
        return j

    def test_bytes_format(self):
        from main import format_job_response
        r = format_job_response(self._make_job(data_transferred=500))
        assert r.data_transferred == "500 B"

    def test_kb_format(self):
        from main import format_job_response
        r = format_job_response(self._make_job(data_transferred=2048))
        assert "KB" in r.data_transferred

    def test_mb_format(self):
        from main import format_job_response
        r = format_job_response(self._make_job(data_transferred=2 * 1024 * 1024))
        assert "MB" in r.data_transferred

    def test_gb_format(self):
        from main import format_job_response
        r = format_job_response(self._make_job(data_transferred=2 * 1024**3))
        assert "GB" in r.data_transferred

    def test_progress_calculation(self):
        from main import format_job_response
        r = format_job_response(self._make_job(total_mailboxes=10, completed=7, failed=3))
        assert r.progress == 100  # (7+3)/10 = 100%

    def test_progress_partial(self):
        from main import format_job_response
        r = format_job_response(self._make_job(total_mailboxes=10, completed=3, failed=0))
        assert r.progress == 30

    def test_progress_zero_total(self):
        from main import format_job_response
        r = format_job_response(self._make_job(total_mailboxes=0, completed=0, failed=0))
        assert r.progress == 0

    def test_none_name_becomes_untitled(self):
        from main import format_job_response
        r = format_job_response(self._make_job(name=None))
        assert r.name == "Untitled"


# =====================================================================
# _sync_job_runtime — Status Derivation
# =====================================================================
class TestSyncJobRuntime:
    def _make_job_obj(self, **kw):
        defaults = dict(status="pending", total_mailboxes=0, completed=0, failed=0)
        defaults.update(kw)
        return MagicMock(**defaults)

    def test_running_when_running_count(self):
        from main import _sync_job_runtime
        job = self._make_job_obj(status="pending", total_mailboxes=5, completed=0, failed=0)
        changed = _sync_job_runtime(job, {"running": 2, "pending": 3})
        assert job.status == "running"

    def test_completed_when_all_done(self):
        from main import _sync_job_runtime
        job = self._make_job_obj(status="running", total_mailboxes=5, completed=3, failed=0)
        _sync_job_runtime(job, {"success": 3, "warning": 1, "failed": 1})
        assert job.status == "completed"

    def test_failed_when_all_failed(self):
        from main import _sync_job_runtime
        job = self._make_job_obj(status="running", total_mailboxes=3, completed=0, failed=0)
        _sync_job_runtime(job, {"failed": 3})
        assert job.status == "failed"

    def test_running_when_pending_remain(self):
        from main import _sync_job_runtime
        job = self._make_job_obj(status="pending", total_mailboxes=5, completed=0, failed=0)
        _sync_job_runtime(job, {"success": 2, "pending": 3})
        assert job.status == "running"

    def test_empty_counts_no_change(self):
        from main import _sync_job_runtime
        job = self._make_job_obj(status="pending", total_mailboxes=0)
        _sync_job_runtime(job, {})
        assert job.status == "pending"


# =====================================================================
# normalize_managed_username / password
# =====================================================================
class TestNormalizeHelpers:
    def test_valid_username(self):
        from main import normalize_managed_username
        assert normalize_managed_username("john_doe") == "john_doe"
        assert normalize_managed_username("user.name-123") == "user.name-123"

    def test_invalid_username_special_chars(self):
        from main import normalize_managed_username
        with pytest.raises(HTTPException) as exc:
            normalize_managed_username("bad@user!")
        assert exc.value.status_code == 400

    def test_username_too_short(self):
        from main import normalize_managed_username
        with pytest.raises(HTTPException) as exc:
            normalize_managed_username("ab")
        assert exc.value.status_code == 400

    def test_username_too_long(self):
        from main import normalize_managed_username
        with pytest.raises(HTTPException) as exc:
            normalize_managed_username("a" * 33)
        assert exc.value.status_code == 400

    def test_username_strips_whitespace(self):
        from main import normalize_managed_username
        assert normalize_managed_username("  validuser  ") == "validuser"

    def test_password_valid(self):
        from main import normalize_managed_password
        assert normalize_managed_password("longpassword") == "longpassword"

    def test_password_too_short(self):
        from main import normalize_managed_password
        with pytest.raises(HTTPException) as exc:
            normalize_managed_password("short")
        assert exc.value.status_code == 400

    def test_password_strips_whitespace(self):
        from main import normalize_managed_password
        assert normalize_managed_password("  longpassword  ") == "longpassword"


# =====================================================================
# is_root_admin
# =====================================================================
class TestIsRootAdmin:
    def test_root_admin_true(self):
        from main import is_root_admin_username
        assert is_root_admin_username("phongdh") is True

    def test_root_admin_false(self):
        from main import is_root_admin_username
        assert is_root_admin_username("other_user") is False

    def test_root_admin_empty(self):
        from main import is_root_admin_username
        assert is_root_admin_username("") is False

    def test_root_admin_none(self):
        from main import is_root_admin_username
        assert is_root_admin_username(None) is False
