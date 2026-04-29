"""
Test Suite: Worker — Imapsync Command Builder, Exit Codes, Security
Maps to: IM-01 → IM-44
"""
import pytest, os, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from unittest.mock import MagicMock
from worker import build_imapsync_command, secure_delete_file, cleanup_stale_passfiles, _detect_provider, _host_matches, _provider_tuning

def _make_job(**kw):
    d = dict(source_host="imap.gmail.com", target_host="imap.yandex.com", source_port=993, target_port=993, source_security="SSL/TLS", target_security="SSL/TLS", options=None)
    d.update(kw); return MagicMock(**d)

def _make_mb(**kw):
    d = dict(source_user="src@gmail.com", target_user="tgt@yandex.com")
    d.update(kw); return MagicMock(**d)

class TestProviderDetection:
    def test_gmail(self): assert _detect_provider("imap.gmail.com") == "gmail"
    def test_googlemail(self): assert _detect_provider("imap.googlemail.com") == "gmail"
    def test_office365(self): assert _detect_provider("outlook.office365.com") == "office365"
    def test_yandex(self): assert _detect_provider("imap.yandex.com") == "yandex"
    def test_generic(self): assert _detect_provider("mail.custom.vn") == "generic"
    def test_none(self): assert _detect_provider(None) == "generic"
    def test_host_matches_true(self): assert _host_matches("imap.gmail.com", "gmail.com")
    def test_host_matches_false(self): assert not _host_matches("imap.yandex.com", "gmail.com")
    def test_host_matches_none(self): assert not _host_matches(None, "gmail.com")

class TestProviderTuning:
    def test_gmail(self):
        t = _provider_tuning("imap.gmail.com", "imap.gmail.com")
        assert t["split"] == 120 and t["timeout"] == 240
    def test_office365(self):
        t = _provider_tuning("outlook.office365.com", "outlook.office365.com")
        assert t["split"] == 80 and t["timeout"] == 300
    def test_cross_provider(self):
        t = _provider_tuning("imap.gmail.com", "outlook.office365.com")
        assert t["split"] == 80 and t["timeout"] == 300

class TestBuildCommand:
    def _b(self, jkw=None, opts=None):
        return build_imapsync_command(_make_job(**(jkw or {})), _make_mb(), "/tmp/p1", "/tmp/p2", opts or {})

    def test_basic_hosts(self):
        cmd, _ = self._b(); i = cmd.index("--host1"); assert cmd[i+1] == "imap.gmail.com"
    def test_ssl1(self): cmd, _ = self._b({"source_security": "SSL/TLS"}); assert "--ssl1" in cmd
    def test_tls1(self): cmd, _ = self._b({"source_security": "STARTTLS"}); assert "--tls1" in cmd
    def test_ssl2(self): cmd, _ = self._b({"target_security": "SSL/TLS"}); assert "--ssl2" in cmd
    def test_tls2(self): cmd, _ = self._b({"target_security": "STARTTLS"}); assert "--tls2" in cmd
    def test_no_sec(self):
        cmd, _ = self._b({"source_security": "None", "target_security": "None"})
        for f in ["--ssl1","--tls1","--ssl2","--tls2"]: assert f not in cmd
    def test_gmail1(self): cmd, _ = self._b({"source_host": "imap.gmail.com"}); assert "--gmail1" in cmd
    def test_gmail2(self): cmd, _ = self._b({"target_host": "imap.gmail.com"}); assert "--gmail2" in cmd
    def test_office1(self): cmd, _ = self._b({"source_host": "outlook.office365.com"}); assert "--office3651" in cmd
    def test_office2(self): cmd, _ = self._b({"target_host": "outlook.office365.com"}); assert "--office3652" in cmd
    def test_syncinternaldates(self): cmd, _ = self._b(opts={"sync_internal_dates": True}); assert "--syncinternaldates" in cmd
    def test_skip_trash(self):
        cmd, _ = self._b(opts={"skip_trash": True})
        vals = [cmd[i+1] for i, x in enumerate(cmd) if x == "--exclude"]
        assert "Trash" in vals
    def test_dry_run(self): cmd, _ = self._b(opts={"dry_run": True}); assert "--dry" in cmd
    def test_no_opts(self):
        cmd, _ = self._b(opts={})
        for f in ["--syncinternaldates","--dry","--exclude"]: assert f not in cmd
    def test_always_present(self):
        cmd, _ = self._b()
        for f in ["--automap","--useuid","--skipcrossduplicates","--nofoldersizes","--fastio1","--fastio2"]: assert f in cmd
    def test_exchange1(self): cmd, _ = self._b({"source_host": "mail.exchange.co"}); assert "--exchange1" in cmd
    def test_zoho2(self): cmd, _ = self._b({"target_host": "imap.zoho.com"}); assert "--zoho2" in cmd

class TestSecureDelete:
    def test_delete_file(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f: f.write("secret"); p = f.name
        secure_delete_file(p); assert not os.path.exists(p)
    def test_nonexistent(self): secure_delete_file("/nonexistent/xxx")
    def test_none(self): secure_delete_file(None)
    def test_empty(self): secure_delete_file("")

class TestCleanup:
    def test_old_files_cleaned(self):
        p = os.path.join(tempfile.gettempdir(), "isp_test_stale")
        with open(p, "w") as f: f.write("x")
        os.utime(p, (time.time()-7200, time.time()-7200))
        cleanup_stale_passfiles(); assert not os.path.exists(p)
    def test_recent_files_kept(self):
        p = os.path.join(tempfile.gettempdir(), "isp_test_recent")
        with open(p, "w") as f: f.write("x")
        cleanup_stale_passfiles(); assert os.path.exists(p); os.unlink(p)
