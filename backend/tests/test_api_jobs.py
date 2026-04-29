"""
Test Suite: API — Jobs & Mailboxes
Maps to: CJ-01→03, DB-01→05, JD-01→05, PR-04→06, SYS-01
"""
import pytest, os, sys, io, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from unittest.mock import patch

# =====================================================================
# Job CRUD (CJ-01→03, DB-02→05)
# =====================================================================
class TestJobCRUD:
    def test_create_job(self, admin_client):
        """CJ-01: Create job returns ID and status."""
        c, csrf = admin_client
        r = c.post("/api/jobs", json={"name": "Test", "source_host": "imap.gmail.com",
            "target_host": "imap.yandex.com", "password": "pass1234"}, headers={"X-CSRF-Token": csrf})
        assert r.status_code == 200
        b = r.json()
        assert "id" in b; assert b["status"] == "running"; assert b["source"] == "imap.gmail.com"

    def test_create_job_with_password(self, admin_client):
        """CJ-03: Job with password sets cookie."""
        c, csrf = admin_client
        r = c.post("/api/jobs", json={"name": "PW Job", "source_host": "a.com",
            "target_host": "b.com", "password": "securepass"}, headers={"X-CSRF-Token": csrf})
        assert r.status_code == 200
        assert "job_password" in r.cookies

    def test_list_jobs(self, sample_job):
        """DB-02: List jobs returns created jobs."""
        c, csrf, jid, _ = sample_job
        r = c.get("/api/jobs")
        assert r.status_code == 200
        jobs = r.json()
        assert len(jobs) >= 1
        assert any(j["id"] == jid for j in jobs)

    def test_delete_single_job(self, sample_job, db_session):
        """DB-03: Delete a non-running job succeeds."""
        c, csrf, jid, _ = sample_job
        # Directly set job to completed since cancel only works with running mailboxes
        from database import Job
        job = db_session.query(Job).filter(Job.id == jid).first()
        job.status = "completed"
        db_session.commit()
        r = c.delete(f"/api/jobs/{jid}", headers={"X-CSRF-Token": csrf})
        assert r.status_code == 200

    def test_delete_running_job_blocked(self, sample_job):
        """DB-05: Cannot delete a running job."""
        c, csrf, jid, _ = sample_job
        r = c.delete(f"/api/jobs/{jid}", headers={"X-CSRF-Token": csrf})
        assert r.status_code == 400
        assert "running" in r.json()["detail"].lower()

    def test_delete_all_jobs_blocked_when_running(self, sample_job):
        """Cannot delete all when jobs are running."""
        c, csrf, _, _ = sample_job
        r = c.delete("/api/jobs", headers={"X-CSRF-Token": csrf})
        assert r.status_code == 400

    def test_get_job_not_found(self, admin_client):
        """404 for non-existent job."""
        c, _ = admin_client
        r = c.get("/api/jobs/nonexistent-id")
        assert r.status_code == 404

# =====================================================================
# Job Password Verification (JD-01→02)
# =====================================================================
class TestJobPassword:
    def test_get_job_correct_password(self, sample_job):
        """JD-01: Access job with correct password."""
        c, csrf, jid, pw = sample_job
        r = c.get(f"/api/jobs/{jid}", params={"password": pw})
        assert r.status_code == 200
        assert r.json()["id"] == jid

    def test_get_job_wrong_password(self, sample_job):
        """JD-02: Wrong password returns 401."""
        c, csrf, jid, _ = sample_job
        r = c.get(f"/api/jobs/{jid}", params={"password": "wrong"})
        assert r.status_code == 401

    def test_get_job_no_password(self, sample_job):
        """No password when required returns 401."""
        c, csrf, jid, _ = sample_job
        # Clear cookies to remove any stored password
        c.cookies.clear()
        # Re-login
        c.post("/api/login", data={"username": "phongdh", "password": "testadmin123"})
        r = c.get(f"/api/jobs/{jid}")
        assert r.status_code == 401

    def test_verify_password_endpoint(self, sample_job):
        """POST /api/jobs/{id}/verify sets cookie on success."""
        c, csrf, jid, pw = sample_job
        r = c.post(f"/api/jobs/{jid}/verify", json={"password": pw})
        assert r.status_code == 200
        assert r.json()["valid"] is True

    def test_verify_password_wrong(self, sample_job):
        """Verify with wrong password returns 401."""
        c, csrf, jid, _ = sample_job
        r = c.post(f"/api/jobs/{jid}/verify", json={"password": "wrong"})
        assert r.status_code == 401

# =====================================================================
# Mailbox Operations (JD-03→05)
# =====================================================================
class TestMailboxOps:
    @patch("main.executor")
    def test_add_single_mailbox(self, mock_exec, sample_job):
        """JD-03: Add mailbox to job."""
        c, csrf, jid, pw = sample_job
        r = c.post(f"/api/jobs/{jid}/mailboxes", json={
            "source_user": "src@gmail.com", "source_pass": "p1",
            "target_user": "tgt@yandex.com", "target_pass": "p2"
        }, headers={"X-CSRF-Token": csrf})
        assert r.status_code == 200
        assert "mailbox_id" in r.json()
        mock_exec.submit.assert_called_once()

    @patch("main.executor")
    def test_upload_csv(self, mock_exec, sample_job):
        """JD-04: Upload CSV creates mailboxes."""
        c, csrf, jid, _ = sample_job
        csv_content = "src1@g.com,pass1,tgt1@y.com,pass2\nsrc2@g.com,pass3,tgt2@y.com,pass4\n"
        r = c.post(f"/api/upload/{jid}",
            files={"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")},
            headers={"X-CSRF-Token": csrf})
        assert r.status_code == 200
        assert "2" in r.json()["message"]

    @patch("main.executor")
    def test_upload_csv_invalid_rows_skipped(self, mock_exec, sample_job):
        """JD-05: Rows with <4 cols are skipped."""
        c, csrf, jid, _ = sample_job
        csv_content = "only_email\nsrc@g.com,p1,tgt@y.com,p2\n"
        r = c.post(f"/api/upload/{jid}",
            files={"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")},
            headers={"X-CSRF-Token": csrf})
        assert r.status_code == 200
        assert "1" in r.json()["message"]  # Only 1 valid row

# =====================================================================
# Stop / Retry / Cancel (PR-04→06)
# =====================================================================
class TestProcessControl:
    @patch("main.executor")
    def test_stop_mailbox(self, mock_exec, sample_job):
        """PR-04: Stop a running mailbox."""
        c, csrf, jid, _ = sample_job
        # Add a mailbox first
        r = c.post(f"/api/jobs/{jid}/mailboxes", json={
            "source_user": "s@g.com", "source_pass": "p",
            "target_user": "t@y.com", "target_pass": "p"
        }, headers={"X-CSRF-Token": csrf})
        mb_id = r.json()["mailbox_id"]
        r2 = c.post(f"/api/mailboxes/{mb_id}/stop", headers={"X-CSRF-Token": csrf})
        assert r2.status_code == 200

    @patch("main.executor")
    def test_retry_mailbox(self, mock_exec, sample_job):
        """PR-05: Retry a failed mailbox."""
        c, csrf, jid, _ = sample_job
        r = c.post(f"/api/jobs/{jid}/mailboxes", json={
            "source_user": "s@g.com", "source_pass": "p",
            "target_user": "t@y.com", "target_pass": "p"
        }, headers={"X-CSRF-Token": csrf})
        mb_id = r.json()["mailbox_id"]
        # Stop it first so we can retry
        c.post(f"/api/mailboxes/{mb_id}/stop", headers={"X-CSRF-Token": csrf})
        r2 = c.post(f"/api/mailboxes/{mb_id}/retry", headers={"X-CSRF-Token": csrf})
        assert r2.status_code == 200
        assert r2.json()["status"] == "pending"

    def test_cancel_job(self, sample_job):
        """PR-06: Cancel all running mailboxes."""
        c, csrf, jid, _ = sample_job
        r = c.post(f"/api/jobs/{jid}/cancel", headers={"X-CSRF-Token": csrf})
        assert r.status_code == 200

# =====================================================================
# Stats & Health (DB-01, SYS-01)
# =====================================================================
class TestStatsAndHealth:
    def test_get_stats(self, admin_client):
        """DB-01: Dashboard stats returns aggregated data."""
        c, _ = admin_client
        r = c.get("/api/stats")
        assert r.status_code == 200
        b = r.json()
        assert "total_jobs" in b
        assert "active_jobs" in b
        assert "completed_mailboxes" in b
        assert "data_transferred" in b

    def test_health_check(self, admin_client):
        """SYS-01: Health check returns system info."""
        c, _ = admin_client
        r = c.get("/api/health")
        assert r.status_code == 200
        b = r.json()
        assert b["status"] == "ok"
        assert "python" in b
        assert "database" in b
